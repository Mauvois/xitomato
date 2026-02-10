<template>
  <div class="panel stack">
    <div class="topbar">
      <h3>Ajouter une task</h3>
      <span class="badge">Rapide</span>
    </div>
    <div class="stack">
      <input v-model="title" class="input" placeholder="Titre" />
      <input v-model.number="estimate" class="input" type="number" min="1" placeholder="Estimation (pomodori)" />
      <textarea v-model="note" class="input" rows="2" placeholder="Note (optionnel)"></textarea>
      <button class="primary" @click="submit" :disabled="!title.trim()">Ajouter</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

const emit = defineEmits(["add"]);

const title = ref("");
const estimate = ref(1);
const note = ref("");

function submit() {
  if (!title.value.trim()) return;
  emit("add", { title: title.value.trim(), estimate_pomodoros: estimate.value, note: note.value || null });
  title.value = "";
  estimate.value = 1;
  note.value = "";
}
</script>
