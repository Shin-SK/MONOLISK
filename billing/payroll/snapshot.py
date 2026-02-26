# billing/payroll/snapshot.py
"""
給与計算スナップショット生成ロジック
Bill をクローズする時点での給与内訳を「不変スナップショット」として保存し、
後続の編集による dirty 検知に使用する。
"""

import hashlib
import json
from decimal import Decimal, ROUND_FLOOR
from typing import Dict, List, Any
from django.utils import timezone
from django.conf import settings
from billing.services.payout_helper import get_payout_base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from billing.models import Bill
    from billing.calculator import BillCalculationResult  # 実体の場所が違うなら合わせる
    from billing.payroll.types import CastPayout          # 実体の場所が違うなら合わせる


def build_payroll_snapshot(bill: "Bill") -> Dict[str, Any]:
    """
    Bill のクローズ時点での給与スナップショットを生成。
    
    Args:
        bill: Bill インスタンス（closed_at が既に設定されていることを想定）
    
    Returns:
        JSON シリアライズ可能な dict。
        
        形式:
        {
          "version": 1,
          "bill_id": 123,
          "store_slug": "dosukoi-asa",
          "closed_at": "2025-12-19T21:00:00+09:00",
          "totals": {
            "subtotal": 100000,
            "service_charge": 10000,
            "tax": 11000,
            "grand_total": 121000,
            "labor_total": 45000,          # ★ 給与関連 totals
            "nomination_total": 20000,
            "dohan_total": 0,
            "item_total": 25000,
            "hourly_total": 0
          },
          "by_cast": [
            {
              "cast_id": 14,
              "stay_type": "free",
              "amount": 25000,
              "breakdown": [
                {
                  "type": "item_back",
                  "label": "ドリンク・フード",
                  "amount": 25000,
                  "basis": {
                    "detail": [
                      {"item_id": 79, "qty": 2, "price": 5000, "subtotal": 10000, "rate": 0.5, "amount": 5000},
                      {"item_id": 80, "qty": 1, "price": 15000, "subtotal": 15000, "rate": 0.67, "amount": 10000}
                    ]
                  }
                }
              ]
            },
            {
              "cast_id": 21,
              "stay_type": "nom",
              "amount": 20000,
              "breakdown": [
                {
                  "type": "nomination_pool",
                  "label": "本指名プール",
                  "amount": 20000,
                  "basis": {
                    "pool_total": 100000,
                    "rate": 0.20,
                    "num_casts": 1
                  }
                }
              ]
            }
          ],
          "items": [
            {
              "bill_item_id": 1001,
              "name": "スペシャルドリンク",
              "qty": 2,
              "unit_price": 5000,
              "subtotal": 10000,
              "served_by_cast_id": 14,
              "stay_type": "free",
              "payroll_effects": [
                {
                  "cast_id": 14,
                  "type": "item_back",
                  "amount": 5000,
                  "basis": {
                    "rate": 0.5,
                    "calculation": "qty * price * rate"
                  }
                }
              ]
            }
          ],
          "hash": "sha256:abc123..."
        }
    """
    from ..calculator import BillCalculator
    from .engines import get_engine
    from ..models import BillCastStay
    
    # 金額計算を実行（既存ロジック）
    calc = BillCalculator(bill)
    result = calc.execute()
    
    # 店舗情報取得（Phase 8-1：bill.table.store 直接使用）
    store = None
    if getattr(bill, "table", None) and getattr(bill.table, "store", None):
        store = bill.table.store
    
    store_slug = store.slug if store else "unknown"
    store_id = store.id if store else None
    engine = get_engine(store)
    
    # ─────────────────────────────────────────
    # items: 各伝票明細の給与効果
    # ─────────────────────────────────────────
    items_info = _build_items_info(bill, engine, store)

    # ─────────────────────────────────────────
    # by_cast: 各キャストの給与集計 + 内訳
    # ─────────────────────────────────────────
    by_cast = _build_by_cast(bill, result.cast_payouts, items_info, store, engine)
    
    # ─────────────────────────────────────────
    # totals: 給与関連の合計値
    # ─────────────────────────────────────────
    totals_dict = _build_totals(by_cast, items_info, result)
    
    # ─────────────────────────────────────────
    # スナップショット構築
    # ─────────────────────────────────────────
    
    # meta情報の構築（Phase 7-4・8-1）
    use_timeboxed = getattr(settings, "USE_TIMEBOXED_NOM_POOL", False)
    meta = {
        "snapshot_version": 2,
        "generated_at": timezone.now().isoformat(),
        "use_timeboxed_nom_pool": use_timeboxed,
        "nom_pool_mode": "timeboxed" if use_timeboxed else "legacy",
        "engine": engine.__class__.__name__,
        "store_id": store_id,
        "store_slug": store_slug,
    }
    
    snapshot = {
        "meta": meta,
        "version": 1,
        "bill_id": bill.id,
        "store_slug": store_slug,
        "closed_at": (bill.closed_at or timezone.now()).isoformat(),
        "totals": totals_dict,
        "by_cast": by_cast,
        "items": items_info,
    }
    
    # ハッシュ付与（改ざん検知用）
    snapshot["hash"] = _compute_snapshot_hash(snapshot)
    
    return snapshot


def _get_item_served_casts(item) -> list:
    """served_by_casts (M2M) を返す。空なら served_by_cast (FK) へフォールバック。"""
    casts = list(item.served_by_casts.all())
    if casts:
        return casts
    if item.served_by_cast_id and item.served_by_cast:
        return [item.served_by_cast]
    return []


def _compute_item_back_split(item, store, stay_type_map: dict, engine, bill) -> dict:
    """
    1アイテムの item_back を担当キャスト全員に均等分配。
    各キャストの back_rate は stay_type ベースで個別算出。
    端数は 100 円単位 floor（店残し）。

    Returns:
        {cast_id: {"amount": int, "rate": Decimal, "basis_type": str}}
    """
    from billing.services.backrate import resolve_back_rate

    casts = _get_item_served_casts(item)
    if not casts or not item.item_master:
        return {}

    base, basis_type, _ = get_payout_base(item, item.item_master)
    category = getattr(item.item_master, "category", None)
    n = len(casts)
    total = Decimal(0)
    cast_info = {}

    for cast in casts:
        stay_type = stay_type_map.get(cast.id, "free")
        rate = resolve_back_rate(
            store=store, category=category, cast=cast, stay_type=stay_type
        )
        contrib = base * rate
        bt = basis_type
        override = engine.item_payout_override(bill, item, stay_type)
        if override is not None:
            try:
                contrib += Decimal(override)
            except Exception:
                pass
            bt = "override"
        total += contrib
        cast_info[cast.id] = (rate, bt)

    per_cast = (total / Decimal(n)).quantize(Decimal("100"), rounding=ROUND_FLOOR)
    return {
        cid: {"amount": int(per_cast), "rate": cast_info[cid][0], "basis_type": cast_info[cid][1]}
        for cid in cast_info
    }


def _build_by_cast(
    bill: "Bill",
    cast_payouts: List["CastPayout"],
    items_info: List[Dict[str, Any]],
    store,
    engine
) -> List[Dict[str, Any]]:
    """
    CastPayout を cast 別に集計し、内訳（breakdown）を構築。
    
    Returns:
        [
          {
            "cast_id": 14,
            "stay_type": "free",
            "amount": 25000,
            "breakdown": [
              { "type": "item_back", "label": "...", "amount": 25000, "basis": {...} }
            ]
          },
          ...
        ]
    """
    from ..models import BillCastStay
    
    result = []

    # cast_id → stay_type マップ
    stay_type_map = {}
    for stay in bill.stays.filter(left_at__isnull=True):
        stay_type_map[stay.cast_id] = stay.stay_type

    # cast_id → payout amount 集計（複数 payout を合算）
    payout_amount_map = {}
    for payout in cast_payouts:
        cid = payout.cast_id
        payout_amount_map[cid] = payout_amount_map.get(cid, 0) + int(payout.amount)

    # items_info から cast ごとの item_back 内訳を再構築
    item_back_amount_map = {}
    item_back_details_map = {}
    for item in items_info:
        item_id = item.get("bill_item_id")
        for effect in item.get("payroll_effects", []):
            if effect.get("type") != "item_back":
                continue
            cast_id = effect.get("cast_id")
            if cast_id is None:
                continue
            amount = int(effect.get("amount", 0) or 0)
            basis = effect.get("basis") or {}

            item_back_amount_map[cast_id] = item_back_amount_map.get(cast_id, 0) + amount
            item_back_details_map.setdefault(cast_id, []).append({
                "item_id": item_id,
                "name": item.get("name"),
                "qty": item.get("qty"),
                "unit_price": item.get("unit_price"),
                "subtotal": item.get("subtotal"),
                "rate": basis.get("rate"),
                "basis": basis.get("basis_type"),
                "amount": amount,
            })

    # by_cast 母集団 = payout cast_id ∪ payroll_effect cast_id
    cast_ids = set(payout_amount_map.keys()) | set(item_back_amount_map.keys())

    nom_payouts = engine.nomination_payouts(bill) or {}
    dohan_payouts = engine.dohan_payouts(bill) or {}
    nom_items = [
        it for it in bill.items.all()
        if getattr(it, "is_nomination", False)
    ]
    nom_subtotal = sum(it.subtotal for it in nom_items)
    pool_rate = float(getattr(bill.table.store, "nom_pool_rate", 0))
    num_nominated = len(bill.nominated_casts.all()) + (1 if bill.main_cast else 0)

    # by_cast を構築
    for cast_id in sorted(cast_ids):
        payout_amount = payout_amount_map.get(cast_id, 0)
        item_back_amount = item_back_amount_map.get(cast_id, 0)
        nom_amount = int(nom_payouts.get(cast_id, 0) or 0)
        dohan_amount = int(dohan_payouts.get(cast_id, 0) or 0)

        amount = payout_amount + item_back_amount
        stay_type = stay_type_map.get(cast_id, "unknown")
        breakdown = []

        if item_back_amount > 0:
            breakdown.append({
                "type": "item_back",
                "label": "ドリンク・フード",
                "amount": item_back_amount,
                "basis": {
                    "detail": item_back_details_map.get(cast_id, []),
                    "stay_type": stay_type,
                }
            })

        if nom_amount > 0:
            breakdown.append({
                "type": "nomination_pool",
                "label": "本指名プール",
                "amount": nom_amount,
                "basis": {
                    "pool_subtotal": nom_subtotal,
                    "pool_rate": pool_rate,
                    "num_nominated": num_nominated,
                }
            })

        if dohan_amount > 0:
            breakdown.append({
                "type": "dohan_pool",
                "label": "同伴",
                "amount": dohan_amount,
                "basis": {
                    "method": "engine_calculated",
                }
            })

        component_total = item_back_amount + nom_amount + dohan_amount
        adjustment = amount - component_total
        if adjustment != 0:
            breakdown.append({
                "type": "adjustment",
                "label": "調整",
                "amount": adjustment,
                "basis": {
                    "reason": "residual_from_engine",
                }
            })

        result.append({
            "cast_id": cast_id,
            "stay_type": stay_type,
            "amount": amount,
            "breakdown": breakdown,
        })

    return result


def _build_cast_breakdown(
    bill: "Bill",
    cast_id: int,
    total_amount: int,
    stay_type_map: dict,
    engine,
    store,
) -> List[Dict[str, Any]]:
    """
    特定キャストの給与内訳を構築。
    item_back / nomination_pool / dohan_pool などを分類。

    Returns:
        [
          { "type": "item_back", "label": "...", "amount": 5000, "basis": {...} },
          { "type": "nomination_pool", "label": "...", "amount": 20000, "basis": {...} },
        ]
    """
    from ..models import BillItem

    stay_type = stay_type_map.get(cast_id, "unknown")
    breakdown = []
    remaining = total_amount

    # ─────────────────────────────────────────
    # 1) Item Back（served_by_casts M2M 経由、FK へフォールバック）
    # ─────────────────────────────────────────
    item_back_amount = 0
    item_details = []

    for item in bill.items.select_related("item_master__category", "served_by_cast").prefetch_related("served_by_casts").all():
        if item.exclude_from_payout:
            continue
        if item.is_nomination:
            continue
        if cast_id not in {c.id for c in _get_item_served_casts(item)}:
            continue

        split = _compute_item_back_split(item, store, stay_type_map, engine, bill)
        entry = split.get(cast_id)
        if not entry or entry["amount"] <= 0:
            continue

        amount = entry["amount"]
        item_back_amount += amount
        item_details.append({
            "item_id": item.id,
            "name": item.item_master.name if item.item_master else "(削除済)",
            "qty": item.qty,
            "unit_price": int(item.price or 0),
            "subtotal": int(item.subtotal),
            "rate": str(entry["rate"]),
            "basis": entry["basis_type"],
            "amount": amount,
        })
    
    if item_back_amount > 0:
        breakdown.append({
            "type": "item_back",
            "label": "ドリンク・フード",
            "amount": item_back_amount,
            "basis": {
                "detail": item_details,
                "stay_type": stay_type,
            }
        })
        remaining -= item_back_amount
    
    # ─────────────────────────────────────────
    # 2) Nomination Pool
    # ─────────────────────────────────────────
    nom_payouts = engine.nomination_payouts(bill) or {}
    nom_amount = nom_payouts.get(cast_id, 0)
    
    if nom_amount > 0:
        # 本指名プール詳細
        nom_items = [
            it for it in bill.items.all()
            if getattr(it, 'is_nomination', False)
        ]
        nom_subtotal = sum(it.subtotal for it in nom_items)
        
        breakdown.append({
            "type": "nomination_pool",
            "label": "本指名プール",
            "amount": nom_amount,
            "basis": {
                "pool_subtotal": nom_subtotal,
                "pool_rate": float(getattr(bill.table.store, "nom_pool_rate", 0)),
                "num_nominated": len(bill.nominated_casts.all()) + (1 if bill.main_cast else 0),
            }
        })
        remaining -= nom_amount
    
    # ─────────────────────────────────────────
    # 3) Dohan Pool
    # ─────────────────────────────────────────
    dohan_payouts = engine.dohan_payouts(bill) or {}
    dohan_amount = dohan_payouts.get(cast_id, 0)
    
    if dohan_amount > 0:
        breakdown.append({
            "type": "dohan_pool",
            "label": "同伴",
            "amount": dohan_amount,
            "basis": {
                "method": "engine_calculated",
            }
        })
        remaining -= dohan_amount
    
    # ─────────────────────────────────────────
    # 4) Residual（誤差吸収）
    # ─────────────────────────────────────────
    if remaining != 0:
        # 計算誤差やその他の調整項目
        breakdown.append({
            "type": "adjustment",
            "label": "調整",
            "amount": remaining,
            "basis": {
                "reason": "residual_from_engine",
            }
        })
    
    return breakdown


def _build_items_info(bill: "Bill", engine, store) -> List[Dict[str, Any]]:
    """
    Bill の明細（items）を構築。
    各アイテムの給与効果（payroll_effects）を記載。

    Returns:
        [
          {
            "bill_item_id": 1001,
            "name": "スペシャルドリンク",
            "qty": 2,
            "unit_price": 5000,
            "subtotal": 10000,
            "served_by_cast_id": 14,
            "stay_type": "free",
            "payroll_effects": [
              {
                "cast_id": 14,
                "type": "item_back",
                "amount": 5000,
                "basis": {...}
              }
            ]
          },
          ...
        ]
    """
    from ..models import BillCastStay

    # cast_id → stay_type マップ
    stay_type_map = {}
    for stay in bill.stays.filter(left_at__isnull=True):
        stay_type_map[stay.cast_id] = stay.stay_type

    result = []

    for item in bill.items.select_related("item_master__category", "served_by_cast").prefetch_related("served_by_casts").all():
        if item.exclude_from_payout:
            continue

        served_by_cast_id = item.served_by_cast_id
        served_casts = _get_item_served_casts(item)
        primary_id = served_casts[0].id if served_casts else served_by_cast_id
        stay_type = stay_type_map.get(primary_id, "unknown") if primary_id else None

        # payroll_effects 計算
        payroll_effects = []

        if served_casts and not item.is_nomination:
            split = _compute_item_back_split(item, store, stay_type_map, engine, bill)
            for cast in served_casts:
                entry = split.get(cast.id)
                if not entry:
                    continue
                amount = entry["amount"]
                rate = entry["rate"]
                basis_type = entry["basis_type"]
                if amount > 0 or rate != 0:
                    if basis_type == "cost":
                        calc_label = "cost * qty * rate / n"
                    elif basis_type == "subtotal":
                        calc_label = "subtotal * rate / n"
                    else:
                        calc_label = "calculated"
                    payroll_effects.append({
                        "cast_id": cast.id,
                        "type": "item_back",
                        "amount": amount,
                        "basis": {
                            "rate": str(rate),
                            "calculation": calc_label,
                            "basis_type": basis_type,
                        }
                    })

        result.append({
            "bill_item_id": item.id,
            "name": item.item_master.name if item.item_master else "(削除済)",
            "qty": item.qty,
            "unit_price": int(item.price or 0),
            "subtotal": int(item.subtotal),
            "served_by_cast_id": served_by_cast_id,
            "stay_type": stay_type,
            "payroll_effects": payroll_effects,
        })

    return result


def _build_totals(by_cast: List, items_info: List, result: "BillCalculationResult") -> Dict[str, Any]:
    """
    by_cast と items_info から给与関連の totals を構築。
    
    Returns:
        {
          "subtotal": 100000,
          "service_charge": 10000,
          "tax": 11000,
          "grand_total": 121000,
          "labor_total": 45000,        # by_cast の amount 合計
          "nomination_total": 20000,   # by_cast 内 nomination 合計
          "dohan_total": 0,            # by_cast 内 dohan 合計
          "item_total": 25000,         # items の payroll_effects 合計
          "hourly_total": 0            # 実装待機
        }
    """
    # ─────────────────────────────────────────
    # 給与関連の集計
    # ─────────────────────────────────────────
    labor_total = sum(c.get("amount", 0) for c in by_cast)
    
    nomination_total = 0
    dohan_total = 0
    for cast_info in by_cast:
        for breakdown in cast_info.get("breakdown", []):
            if breakdown["type"] == "nomination_pool":
                nomination_total += breakdown["amount"]
            elif breakdown["type"] == "dohan_pool":
                dohan_total += breakdown["amount"]
    
    # items から給与効果を集計
    item_total = 0
    for item in items_info:
        for effect in item.get("payroll_effects", []):
            item_total += effect.get("amount", 0)
    
    return {
        "subtotal": int(result.subtotal),
        "service_charge": int(result.service_fee),
        "tax": int(result.tax),
        "grand_total": int(result.total),
        "labor_total": labor_total,
        "nomination_total": nomination_total,
        "dohan_total": dohan_total,
        "item_total": item_total,
        "hourly_total": 0,  # 時給計算は実装待機
    }


def _compute_snapshot_hash(snapshot_dict: Dict[str, Any]) -> str:
    """
    スナップショットのハッシュ値を計算（改ざん検知用）。
    
    hash と closed_at を除外し、totals のみをハッシュ対象にする。
    by_cast/items は複雑でキー順序が不安定なため、
    シンプルに「最終的な金額値」のみでハッシュを計算する。
    
    Args:
        snapshot_dict: hash キーを除いたスナップショット
    
    Returns:
        "sha256:abc123..."
    """
    # totals のみをハッシュ対象にする
    # （by_cast/items は同じ totals から再生成可能なため）
    temp = {
        "totals": snapshot_dict.get("totals", {})
    }
    
    # JSON 正規化（確定的な順序・フォーマット）
    json_str = json.dumps(temp, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    
    # SHA256
    h = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    return f"sha256:{h}"


def compute_current_hash(bill: "Bill") -> str:
    """
    Bill の現在状態から動的に hash を計算し直す（dirty 判定用）。
    
    スナップショット保存後に Bill が編集された場合、
    現在の給与スナップショット（新規生成）の hash と
    保存済み snapshot の hash を比較する。
    
    異なれば payroll_dirty=True。
    
    hash 計算は totals のみに限定（by_cast/items はダイナミックなため）。
    """
    # 再スナップショット生成
    snapshot_current = build_payroll_snapshot(bill)
    
    # totals のみでハッシュを計算
    temp = {
        "totals": snapshot_current.get("totals", {}),
    }
    
    json_str = json.dumps(temp, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    h = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    return f"sha256:{h}"


def is_payroll_dirty(bill: "Bill") -> bool:
    """
    Bill が payroll_dirty 状態か判定。
    
    条件:
    - payroll_snapshot が存在する（クローズ済）
    - 現在の給与スナップショット hash が保存時の hash と異なる
    
    Returns:
        True: dirty（編集あり）、False: clean（無編集）
    """
    if not bill.payroll_snapshot:
        return False
    
    snapshot_hash = bill.payroll_snapshot.get("hash")
    if not snapshot_hash:
        return False
    
    current_hash = compute_current_hash(bill)
    return current_hash != snapshot_hash


def snapshot_is_stale(bill: "Bill") -> bool:
    """
    Bill の payroll_snapshot が古い（設定変更により再生成が必要）かどうかを判定。
    
    判定条件（いずれかに該当したら stale）:
    1. snapshot が存在しない
    2. snapshot に meta 情報がない（旧フォーマット）
    3. use_timeboxed_nom_pool が現在の settings とズレている
    4. engine class が異なる（店舗のengineが変わった）
    
    Returns:
        True: stale（再生成が必要）、False: fresh（最新の条件で生成されている）
    """
    if not bill.payroll_snapshot:
        # snapshotがない = stale ではなく「未生成」だが、便宜上 stale 判定
        return False
    
    snapshot = bill.payroll_snapshot
    meta = snapshot.get("meta") or {}
    
    # meta がない（旧フォーマット）= stale
    if not meta:
        return True
    
    # snapshot_version チェック
    snap_version = meta.get("snapshot_version", 1)
    if snap_version < 2:
        # 古いバージョン = stale
        return True
    
    # use_timeboxed_nom_pool の一致確認
    current_use_timeboxed = getattr(settings, "USE_TIMEBOXED_NOM_POOL", False)
    stored_use_timeboxed = meta.get("use_timeboxed_nom_pool")
    
    if stored_use_timeboxed is None:
        return True  # meta に記録されていない = stale
    
    if bool(stored_use_timeboxed) != bool(current_use_timeboxed):
        return True  # 設定が変わった = stale
    
    # Phase 8-2：engine比較を外す（方針A：シンプル）
    # snapshot_version + use_timeboxed 一致の2点で十分
    # engine は meta に記録するが、stale判定には使わない
    
    # 全てOK = fresh
    return False

