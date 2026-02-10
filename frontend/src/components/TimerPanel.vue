<template>
  <div class="panel stack timer-panel" @click="emit('focus')">
    <div class="topbar" v-if="currentKindLabel">
      <span class="badge">{{ currentKindLabel }}</span>
    </div>
    <div class="timer-display">{{ displayTime }}</div>
    <small v-if="currentTitle">{{ currentTitle }}</small>
    <div v-if="!collapsed" class="stack">
      <input v-model="sessionTitle" class="input input--medium" placeholder="Nouveau pomodoro" />
      <div class="row">
        <button class="primary" @click="() => onStart(25)" :disabled="isRunning">Focus 25 min</button>
        <button class="primary" @click="() => onStart(45)" :disabled="isRunning">Focus 45 min</button>
        <button class="secondary" @click="onStop" :disabled="!isRunning">Stop</button>
      </div>
      <div class="row">
        <button class="secondary" @click="() => onAdjust(5)" :disabled="!currentSession">+5 min</button>
        <button class="secondary" @click="() => onAdjust(-5)" :disabled="!currentSession">-5 min</button>
      </div>
      <div class="stack">
        <select v-model.number="selectedTaskId" class="input input--medium">
          <option :value="null">Tache (optionnel)</option>
          <option v-for="task in tasks" :key="task.id" :value="task.id">
            {{ task.title }}
          </option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  currentSession: { type: Object, default: null },
  remainingSeconds: { type: Number, default: 0 },
  isRunning: { type: Boolean, default: false },
  collapsed: { type: Boolean, default: false }
});

const emit = defineEmits(["start", "stop", "adjust", "task-change", "focus"]);

const selectedTaskId = ref(null);
const sessionTitle = ref("");

watch(
  () => props.currentSession,
  (value) => {
    selectedTaskId.value = value?.task_id ?? null;
  },
  { immediate: true }
);

watch(selectedTaskId, (value) => {
  emit("task-change", value);
});

const displayTime = computed(() => {
  const minutes = Math.floor(props.remainingSeconds / 60);
  const seconds = props.remainingSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
});

const currentKindLabel = computed(() => {
  if (!props.currentSession) return "";
  return props.currentSession.kind === "focus" ? "Focus" : "Pause";
});

const currentTitle = computed(() => {
  if (!props.currentSession) return "";
  if (props.currentSession.title) return props.currentSession.title;
  if (!props.currentSession.task_id) return "";
  const task = props.tasks.find((item) => item.id === props.currentSession.task_id);
  return task ? task.title : "";
});

function onStart(minutes) {
  emit("start", { taskId: selectedTaskId.value, minutes, title: sessionTitle.value || null });
  sessionTitle.value = "";
}

function onStop() {
  emit("stop");
}

function onAdjust(delta) {
  emit("adjust", delta);
}

</script>
