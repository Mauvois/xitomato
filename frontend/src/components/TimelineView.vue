<template>
  <div class="panel timeline">
    <div class="timeline-grid">
      <div
        v-for="part in daypartList"
        :key="part.name"
        class="timeline-col"
        @dragover.prevent
        @drop="onDrop(part.name, today)"
      >
        <strong>{{ part.name }}</strong>
        <div
          v-for="session in sessionsByDaypart[part.name] || []"
          :key="session.id"
          class="session-pill"
          :class="{ break: session.kind === 'break', planned: session.state === 'planned' }"
          draggable="true"
          @dragstart="onDrag(session)"
          @click="emit('select', session)"
        >
          {{ labelFor(session) }} · {{ timeFor(session) }} · {{ session.planned_minutes }} min
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  dayparts: { type: Array, default: () => [] },
  selectedDate: { type: String, default: "" }
});

const emit = defineEmits(["move", "select"]);

const dragged = ref(null);
const today = computed(() => props.selectedDate || new Date().toISOString().slice(0, 10));

const daypartList = computed(() =>
  props.dayparts.length
    ? props.dayparts
    : [
        { name: "Matin", start: "09:00", end: "12:00" },
        { name: "Apres-midi", start: "13:00", end: "17:00" },
        { name: "Soir", start: "21:30", end: "00:00" }
      ]
);

const sessionsByDaypart = computed(() => {
  const grouped = {};
  props.sessions.forEach((session) => {
    if (session.date !== today.value) return;
    const key = session.daypart_name || "Non defini";
    grouped[key] = grouped[key] || [];
    grouped[key].push(session);
  });
  return grouped;
});


function onDrag(session) {
  dragged.value = session;
}

function onDrop(daypartName, date) {
  if (!dragged.value) return;
  emit("move", { session: dragged.value, daypart_name: daypartName, date });
  dragged.value = null;
}

function labelFor(session) {
  if (session.title) return session.title;
  return session.kind === "focus" ? "Focus" : "Pause";
}

function timeFor(session) {
  if (!session.start_at) return "--:--";
  const dateValue = new Date(session.start_at);
  return `${String(dateValue.getHours()).padStart(2, "0")}:${String(
    dateValue.getMinutes()
  ).padStart(2, "0")}`;
}
</script>
