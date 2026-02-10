<template>
  <div class="modal-backdrop" v-if="open">
    <div class="modal">
      <div class="topbar">
        <h3>Choisir une carte de pause</h3>
        <button class="ghost" @click="emit('close')">Fermer</button>
      </div>
      <p v-if="message">{{ message }}</p>
      <div class="stack">
        <button
          v-for="card in cards"
          :key="card.id"
          class="secondary"
          :disabled="card.remaining_today <= 0"
          @click="emit('select', card)"
        >
          {{ card.name }} · {{ card.remaining_today }}/{{ card.daily_quota }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  open: { type: Boolean, default: false },
  cards: { type: Array, default: () => [] },
  message: { type: String, default: "" }
});

const emit = defineEmits(["select", "close"]);
</script>
