<template>
  <div class="panel stack">
    <div class="topbar">
      <h3>{{ title }}</h3>
      <div class="row">
        <span class="badge">{{ sessions.length }}</span>
        <button v-if="showClear" class="ghost" @click="emit('clear')">Effacer historique</button>
      </div>
    </div>
    <div class="cards">
      <div v-for="session in sessions" :key="session.id" class="card">
        <strong>{{ session.kind === "focus" ? "Focus" : "Pause" }}</strong>
        <small v-if="session.title">{{ session.title }}</small>
        <small>
          {{ session.daypart_name }} · {{ session.planned_minutes }} min · {{ session.state }}
        </small>
        <small v-if="session.task_id">Task #{{ session.task_id }}</small>
        <textarea
          class="input"
          rows="2"
          v-model="notes[session.id]"
          placeholder="Note"
          @blur="onSave(session.id)"
        ></textarea>
      </div>
      <div v-if="sessions.length === 0" class="card">
        <small>Aucune session.</small>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  title: { type: String, default: "Sessions" },
  showClear: { type: Boolean, default: false }
});

const emit = defineEmits(["update-note", "clear"]);

const notes = reactive({});

watch(
  () => props.sessions,
  (value) => {
    value.forEach((session) => {
      notes[session.id] = session.note || "";
    });
  },
  { immediate: true }
);

function onSave(id) {
  emit("update-note", { id, note: notes[id] });
}
</script>
