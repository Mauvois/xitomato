<template>
  <div class="panel stack planner-panel">
    <div class="topbar">
      <span v-if="plannedSessions.length" class="badge">
        {{ plannedSessions.length }} prevues
      </span>
      <div class="row">
        <button v-if="!showForm" class="ghost" @click="showForm = true">Ajouter une session</button>
      </div>
    </div>

    <div v-if="showForm" class="stack planner-form">
      <input v-model="title" class="input input--medium" placeholder="Pomodoro a planifier" />
      <select v-model.number="taskId" class="input input--medium">
        <option :value="null">Tache (optionnel)</option>
        <option v-for="task in tasks" :key="task.id" :value="task.id">
          {{ task.title }}
        </option>
      </select>
      <div class="row">
        <input
          v-model.number="minutes"
          class="input input--small"
          type="number"
          min="1"
          placeholder="Minutes"
        />
        <input v-model="plannedTime" class="input input--small" type="time" />
      </div>
      <div v-if="limitWarning" class="card">
        <small>
          La session depasse le creneau {{ limitWarning.daypart }}. Temps restant: {{
            limitWarning.remaining
          }} min.
        </small>
        <div class="row">
          <button class="secondary" @click="planRemaining">
            Planifier {{ limitWarning.remaining }} min
          </button>
          <button class="ghost" @click="limitWarning = null">Annuler</button>
        </div>
      </div>
      <div class="row">
        <button class="primary" @click="plan">Ajouter session manuelle</button>
        <button class="secondary" @click="() => autoPlan(25)">Auto 25 min</button>
        <button class="secondary" @click="() => autoPlan(45)">Auto 45 min</button>
      </div>
    </div>

    <div class="stack">
      <TimelineView
        :sessions="plannedSessions"
        :dayparts="dayparts"
        :selected-date="selectedDate"
        @move="emit('move', $event)"
        @select="selectSession"
      />
    </div>

    <div v-if="selectedSession" class="card">
      <strong>Session selectionnee</strong>
      <input
        v-model="edits[selectedSession.id].title"
        class="input input--medium"
        placeholder="Titre"
        @blur="update(selectedSession)"
      />
      <div class="row">
        <input
          v-model="edits[selectedSession.id].planned_time"
          class="input input--small"
          type="time"
          @change="update(selectedSession)"
        />
        <input
          v-model.number="edits[selectedSession.id].planned_minutes"
          class="input input--small"
          type="number"
          min="1"
          @blur="update(selectedSession)"
        />
      </div>
      <small>
        {{ edits[selectedSession.id].daypart_name }} ·
        {{ edits[selectedSession.id].planned_minutes }} min
      </small>
      <small v-if="selectedSession.task_id">{{ taskTitle(selectedSession.task_id) }}</small>
      <div class="row">
        <button class="secondary" @click="emit('start', selectedSession)">Demarrer</button>
        <button class="ghost" @click="emit('remove', selectedSession)">Supprimer</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import TimelineView from "./TimelineView.vue";

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  dayparts: { type: Array, default: () => [] },
  plannedSessions: { type: Array, default: () => [] },
  defaultMinutes: { type: Number, default: 45 },
  selectedDate: { type: String, default: "" },
  currentSession: { type: Object, default: null }
});

const emit = defineEmits(["plan", "start", "remove", "update", "move", "error", "reset-planned"]);

const taskId = ref(null);
const minutes = ref(props.defaultMinutes);
const plannedTime = ref(props.dayparts[0]?.start || "09:00");
const daypartName = ref("");
const title = ref("");
const edits = reactive({});
const limitWarning = ref(null);
const showForm = ref(true);
const selectedSession = ref(null);

watch(
  () => props.defaultMinutes,
  (value) => {
    minutes.value = value;
  }
);

watch(
  () => props.dayparts,
  (value) => {
    if (value.length) {
      daypartName.value = resolveDaypartName(value, plannedTime.value);
    }
  },
  { immediate: true }
);

watch(
  () => plannedTime.value,
  (value) => {
    daypartName.value = resolveDaypartName(props.dayparts, value);
    limitWarning.value = null;
  }
);

watch(
  () => props.plannedSessions,
  (value) => {
    value.forEach((session) => {
      edits[session.id] = {
        title: session.title || "",
        planned_time: timeFromSession(session),
        planned_minutes: session.planned_minutes,
        daypart_name: session.daypart_name
      };
    });
    if (!value.length) {
      showForm.value = true;
    }
    if (selectedSession.value) {
      selectedSession.value = value.find((item) => item.id === selectedSession.value.id) || null;
    }
  },
  { immediate: true }
);

function plan() {
  if (!daypartName.value) return;
  const remaining = remainingInDaypart(plannedTime.value, daypartName.value, props.dayparts);
  if (remaining !== null && minutes.value > remaining) {
    limitWarning.value = {
      remaining,
      daypart: daypartName.value,
      plannedTime: plannedTime.value
    };
    return;
  }
  emit("plan", {
    kind: "focus",
    task_id: taskId.value,
    minutes: minutes.value,
    title: title.value || null,
    date: props.selectedDate,
    daypart_name: daypartName.value,
    planned_time: plannedTime.value
  });
  taskId.value = null;
  title.value = "";
  limitWarning.value = null;
  showForm.value = false;
}

function autoPlan(duration) {
  if (!props.dayparts.length) return;
  const last = getLastPlanned();
  const baseMinutes = last
    ? last.startMinutes + last.planned_minutes + breakFor(last.planned_minutes)
    : timeToMinutes(roundedNow());
  const runningEndMinutes = runningSessionEndMinutes();
  const effectiveBase =
    runningEndMinutes !== null ? Math.max(baseMinutes, runningEndMinutes) : baseMinutes;
  const next = adjustForGap(effectiveBase, props.dayparts);
  if (!next) {
    emit("error", "Plus de place aujourd'hui pour planifier une session.");
    return;
  }
  const lastPart = last ? resolveDaypartName(props.dayparts, minutesToTime(last.startMinutes)) : null;
  if (lastPart && lastPart !== next.daypart) {
    emit("error", "Pause courte supprimee avant la grande pause.");
  }
  const nextTime = minutesToTime(next.minutes);
  const remaining = remainingInDaypart(nextTime, next.daypart, props.dayparts);
  if (remaining !== null && duration > remaining) {
    limitWarning.value = {
      remaining,
      daypart: next.daypart,
      plannedTime: nextTime,
      duration
    };
    return;
  }
  emit("plan", {
    kind: "focus",
    task_id: taskId.value,
    minutes: duration,
    title: title.value || null,
    date: props.selectedDate,
    daypart_name: next.daypart,
    planned_time: nextTime
  });
  title.value = "";
  plannedTime.value = nextTime;
  limitWarning.value = null;
  showForm.value = false;
}

function taskTitle(taskIdValue) {
  const task = props.tasks.find((item) => item.id === taskIdValue);
  return task ? task.title : `Task #${taskIdValue}`;
}

function resolveDaypartName(dayparts, timeValue) {
  if (!dayparts?.length) return "";
  const [hour, minute] = timeValue.split(":").map(Number);
  const currentMinutes = hour * 60 + minute;
  for (const part of dayparts) {
    const [startHour, startMinute] = part.start.split(":").map(Number);
    const [endHour, endMinute] = part.end.split(":").map(Number);
    const startMinutes = startHour * 60 + startMinute;
    const endMinutes = endHour * 60 + endMinute;
    if (startMinutes <= endMinutes) {
      if (currentMinutes >= startMinutes && currentMinutes < endMinutes) return part.name;
    } else {
      if (currentMinutes >= startMinutes || currentMinutes < endMinutes) return part.name;
    }
  }
  return dayparts[0].name;
}

function timeToMinutes(value) {
  const [hour, minute] = value.split(":").map(Number);
  return hour * 60 + minute;
}

function remainingInDaypart(timeValue, daypart, dayparts) {
  const part = dayparts.find((item) => item.name === daypart);
  if (!part) return null;
  const start = timeToMinutes(part.start);
  let end = timeToMinutes(part.end);
  if (end === 0 || end <= start) end = 1440;
  const current = timeToMinutes(timeValue);
  if (current < start) return end - start;
  if (current >= end) return 0;
  return end - current;
}

function roundedNow() {
  const now = new Date();
  const minutesNow = now.getHours() * 60 + now.getMinutes();
  const rounded = Math.ceil(minutesNow / 5) * 5;
  return minutesToTime(rounded === 1440 ? 1435 : rounded);
}

function planRemaining() {
  if (!limitWarning.value) return;
  emit("plan", {
    kind: "focus",
    task_id: taskId.value,
    minutes: limitWarning.value.remaining,
    title: title.value || null,
    date: props.selectedDate,
    daypart_name: limitWarning.value.daypart,
    planned_time: limitWarning.value.plannedTime
  });
  title.value = "";
  limitWarning.value = null;
  showForm.value = false;
}

onMounted(() => {
  plannedTime.value = roundedNow();
  daypartName.value = resolveDaypartName(props.dayparts, plannedTime.value);
});

function minutesToTime(value) {
  const clamped = Math.max(0, Math.min(1439, value));
  const hour = Math.floor(clamped / 60);
  const minute = clamped % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function breakFor(minutesValue) {
  return minutesValue >= 45 ? 10 : 5;
}

function runningSessionEndMinutes() {
  if (!props.currentSession || props.currentSession.state !== "running") return null;
  if (props.selectedDate !== today()) return null;
  if (!props.currentSession.start_at || !props.currentSession.planned_minutes) return null;
  const now = new Date();
  const startAt = toDate(props.currentSession.start_at);
  const elapsedMinutes = (now.getTime() - startAt.getTime()) / 60000;
  const remainingMinutes = props.currentSession.planned_minutes - elapsedMinutes;
  if (remainingMinutes <= 0) return null;
  const extraBreak = props.currentSession.kind === "focus"
    ? breakFor(props.currentSession.planned_minutes)
    : 0;
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  const endMinutes = nowMinutes + Math.ceil(remainingMinutes) + extraBreak;
  return Math.max(0, Math.min(1439, Math.round(endMinutes)));
}

function getLastPlanned() {
  if (!props.plannedSessions.length) return null;
  const sorted = [...props.plannedSessions]
    .map((session) => ({
      id: session.id,
      planned_minutes: session.planned_minutes,
      startMinutes: timeToMinutes(timeFromSession(session))
    }))
    .sort((a, b) => a.startMinutes - b.startMinutes);
  return sorted[sorted.length - 1];
}

function adjustForGap(startMinutes, dayparts) {
  const ranges = dayparts
    .map((part) => {
      const start = timeToMinutes(part.start);
      let end = timeToMinutes(part.end);
      if (end === 0) end = 1440;
      return { name: part.name, start, end };
    })
    .sort((a, b) => a.start - b.start);

  for (const range of ranges) {
    if (startMinutes >= range.start && startMinutes < range.end) {
      return { minutes: startMinutes, daypart: range.name };
    }
  }

  const next = ranges.find((range) => startMinutes < range.start);
  if (!next) return null;
  return { minutes: next.start, daypart: next.name };
}

function timeFromSession(session) {
  if (!session.start_at) return "09:00";
  const dateValue = new Date(session.start_at);
  return `${String(dateValue.getHours()).padStart(2, "0")}:${String(
    dateValue.getMinutes()
  ).padStart(2, "0")}`;
}

function toDate(value) {
  if (!value) return new Date();
  if (typeof value === "string") {
    const hasZone = value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value);
    return new Date(hasZone ? value : `${value}Z`);
  }
  return new Date(value);
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function update(session) {
  const entry = edits[session.id];
  const daypart = resolveDaypartName(props.dayparts, entry.planned_time);
  entry.daypart_name = daypart;
  emit("update", {
    id: session.id,
    title: entry.title || null,
    planned_time: entry.planned_time,
    planned_minutes: entry.planned_minutes,
    daypart_name: daypart
  });
}

function selectSession(session) {
  selectedSession.value = session;
}
</script>
