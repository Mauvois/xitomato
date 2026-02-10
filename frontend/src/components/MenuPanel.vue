<template>
  <div class="panel app-topbar">
    <div class="brand">
      <img :src="logoUrl" alt="Xitomato" class="brand-logo" />
      <h2>Xitomato</h2>
    </div>
    <div class="nav">
      <button :class="{ active: view === 'home' }" @click="emit('change', 'home')">Accueil</button>
      <button :class="{ active: view === 'tasks' }" @click="emit('change', 'tasks')">Taches</button>
      <button :class="{ active: view === 'history' }" @click="emit('change', 'history')">Historique</button>
      <button :class="{ active: view === 'settings' }" @click="emit('change', 'settings')">Reglages</button>
    </div>
    <div class="time-meta">
      <strong>{{ timeLabel }}</strong>
      <small>{{ dateLabel }}</small>
    </div>
  </div>
</template>

<script setup>
import logoUrl from "../assets/logo.png";

const props = defineProps({
  view: { type: String, default: "home" },
  dateLabel: { type: String, default: "" },
  timeLabel: { type: String, default: "" },
  daypartLabel: { type: String, default: "" }
});

const emit = defineEmits(["change"]);
</script>
