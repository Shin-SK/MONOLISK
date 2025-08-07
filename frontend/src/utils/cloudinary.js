// frontend/src/utils/cloudinary.js
export function avatarUrl(rawUrl, w = 80, h = 80) {
  // Cloudinary URL中の '/upload/' 部分の直後に変換パラメータを挿入
  return rawUrl.replace(
    '/upload/',
    `/upload/f_auto,q_auto,w_${w},h_${h},c_fill/`
  );
}
