<template>
  <div class="panel stack">
    <div class="topbar">
      <div>
        <h2>{{ title }}</h2>
        <small>{{ dateLabel }} · {{ timeLabel }} · {{ daypartLabel }}</small>
      </div>
      <span class="badge">Pause due: {{ pauseDueMinutes }} min</span>
    </div>
    <div class="row">
      <button class="ghost" @click="emit('prev')">Jour precedent</button>
      <button class="secondary" @click="emit('today')">Aujourd'hui</button>
      <button class="ghost" @click="emit('next')">Jour suivant</button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  title: { type: String, default: "Aujourd'hui" },
  dateLabel: { type: String, default: "" },
  timeLabel: { type: String, default: "" },
  daypartLabel: { type: String, default: "" },
  pauseDueMinutes: { type: Number, default: 0 }
});

const emit = defineEmits(["prev", "today", "next"]);
</script>
