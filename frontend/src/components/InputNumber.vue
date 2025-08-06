<template>
  <div class="col-6">
    <label class="form-label">{{ label }}</label>

    <div class="input-group">
      <input
        type="number"
        min="0"
        class="form-control"
        :value="modelValue"
        :readonly="readonly"
        @input="$emit('update:modelValue', +$event.target.value)"
      >
      <span class="input-group-text">円</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: Number, default: 0 },
  label:     String,
  readonly:  Boolean,
})
defineEmits(['update:modelValue'])
</script>
