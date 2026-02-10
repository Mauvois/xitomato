<template>
  <div class="app">
    <MenuPanel
      :view="view"
      :date-label="dateLabel"
      :time-label="timeLabel"
      :daypart-label="currentDaypart"
      @change="view = $event"
    />

    <div class="stack">
      <div v-if="view === 'home'" class="stack">
        <TimerPanel
          :tasks="activeTasks"
          :current-session="currentSession"
          :remaining-seconds="remainingSeconds"
          :is-running="isRunning"
          @start="startFocus"
          @stop="stopCurrent"
          @adjust="adjustCurrent"
          @task-change="updateCurrentTask"
        />
        <PlannerPanel
          :tasks="activeTasks"
          :dayparts="settings?.dayparts || []"
          :planned-sessions="plannedSessions"
          :default-minutes="settings?.default_focus_minutes || 45"
          :selected-date="selectedDate"
          :current-session="currentSession"
          @plan="planSession"
          @start="startPlanned"
          @remove="removePlanned"
          @update="updatePlanned"
          @move="moveSession"
          @error="showToast"
          @reset-planned="resetDay('planned')"
        />
      </div>

      <div v-if="view === 'tasks'" class="stack">
        <TaskQuickAdd @add="addTask" />
        <TaskListView :tasks="tasks" @update="updateTask" @toggle-status="toggleTaskStatus" />
      </div>

      <div v-if="view === 'history'" class="stack">
        <SessionList
          title="Historique"
          :sessions="historySessions"
          :show-clear="true"
          @update-note="updateSessionNote"
          @clear="resetDay('history')"
        />
      </div>

      <SettingsView
        v-if="view === 'settings'"
        :settings="settings"
        :pause-cards="pauseCards"
        :first-run="settings?.needs_setup"
        @save="saveSettings"
        @add-card="addPauseCard"
        @update-card="updatePauseCard"
      />
    </div>

    <PauseCardModal
      :open="showPauseModal"
      :cards="pauseCards"
      :message="pauseMessage"
      @select="consumePause"
      @close="showPauseModal = false"
    />

    <div v-if="toastMessage" class="toast">{{ toastMessage }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { api } from "./api";
import MenuPanel from "./components/MenuPanel.vue";
import TimerPanel from "./components/TimerPanel.vue";
import TaskQuickAdd from "./components/TaskQuickAdd.vue";
import SessionList from "./components/SessionList.vue";
import TaskListView from "./components/TaskListView.vue";
import PauseCardModal from "./components/PauseCardModal.vue";
import SettingsView from "./components/SettingsView.vue";
import PlannerPanel from "./components/PlannerPanel.vue";

const view = ref("home");
const settings = ref(null);
const tasks = ref([]);
const sessions = ref([]);
const pauseCards = ref([]);
const dailyState = ref(null);

const currentSession = ref(null);
const remainingSeconds = ref(0);
const timerId = ref(null);
const clockId = ref(null);
const showPauseModal = ref(false);
const toastMessage = ref("");
const selectedDate = ref(new Date().toISOString().slice(0, 10));
const currentTime = ref(new Date());
const lastFocusMinutes = ref(null);

const isRunning = computed(() => currentSession.value?.state === "running");

const activeTasks = computed(() => tasks.value.filter((task) => task.status === "active"));

const plannedSessions = computed(() =>
  sessions.value.filter((session) => session.state === "planned")
);

const historySessions = computed(() =>
  sessions.value.filter(
    (session) => session.state !== "planned" && session.state !== "running"
  )
);


const dateLabel = computed(() => formatDateLabel(selectedDate.value));
const timeLabel = computed(() => formatTimeLabel(currentTime.value));
const currentDaypart = computed(() =>
  settings.value?.dayparts ? resolveDaypart(settings.value.dayparts, currentTime.value) : ""
);

const pauseMessage = computed(() => {
  if (!pauseCards.value.length) return "Aucune carte configuree";
  const hasAvailable = pauseCards.value.some((card) => card.remaining_today > 0);
  if (!hasAvailable) return "Aucune carte disponible aujourd'hui";
  return "";
});

const today = () => new Date().toISOString().slice(0, 10);

function formatDateLabel(dateString) {
  const dateValue = new Date(`${dateString}T00:00:00`);
  return dateValue.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric"
  });
}

function formatTimeLabel(dateValue) {
  return dateValue.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function parseTime(value) {
  const [hour, minute] = value.split(":").map(Number);
  return { hour, minute };
}

function resolveDaypart(dayparts, dateValue) {
  const currentMinutes = dateValue.getHours() * 60 + dateValue.getMinutes();
  for (const part of dayparts) {
    const start = parseTime(part.start);
    const end = parseTime(part.end);
    const startMinutes = start.hour * 60 + start.minute;
    const endMinutes = end.hour * 60 + end.minute;
    if (startMinutes <= endMinutes) {
      if (currentMinutes >= startMinutes && currentMinutes < endMinutes) {
        return part.name;
      }
    } else {
      if (currentMinutes >= startMinutes || currentMinutes < endMinutes) {
        return part.name;
      }
    }
  }
  return dayparts[0]?.name || "";
}

async function loadAll() {
  settings.value = await api.getSettings();
  tasks.value = await api.listTasks();
  pauseCards.value = await api.listPauseCards();
  await loadDay(selectedDate.value);
  if (settings.value?.needs_setup) {
    view.value = "settings";
  }
}

async function loadDay(dateValue) {
  sessions.value = await api.listSessions(dateValue, dateValue);
  dailyState.value = await api.getDailyState(dateValue);
  if (dateValue === today()) {
    const running = sessions.value.find((session) => session.state === "running");
    if (running) {
      currentSession.value = running;
      startTimer();
    } else {
      currentSession.value = null;
      stopTimer();
    }
  }
}


function startTimer() {
  stopTimer();
  if (!currentSession.value) return;
  updateRemaining();
  timerId.value = setInterval(updateRemaining, 1000);
}

function stopTimer() {
  if (timerId.value) {
    clearInterval(timerId.value);
    timerId.value = null;
  }
}

function updateRemaining() {
  if (!currentSession.value) {
    remainingSeconds.value = 0;
    return;
  }
  const startAt = toDate(currentSession.value.start_at);
  const elapsed = Math.floor((Date.now() - startAt.getTime()) / 1000);
  const planned = currentSession.value.planned_minutes * 60;
  remainingSeconds.value = Math.max(0, planned - elapsed);
  if (remainingSeconds.value === 0 && isRunning.value) {
    onSessionEnded();
  }
}

function toDate(value) {
  if (!value) return new Date();
  if (typeof value === "string") {
    const hasZone = value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value);
    return new Date(hasZone ? value : `${value}Z`);
  }
  return new Date(value);
}

async function startFocus({ taskId, minutes, title }) {
  try {
    if (isRunning.value) {
      showToast("Une session est deja en cours");
      return;
    }
    selectedDate.value = today();
    const session = await api.startSession({ kind: "focus", task_id: taskId, minutes, title });
    currentSession.value = session;
    await loadDay(selectedDate.value);
    startTimer();
  } catch (err) {
    showToast(err.message || "Erreur au demarrage");
  }
}

async function stopCurrent() {
  if (!currentSession.value) return;
  try {
    const session = await api.stopSession(currentSession.value.id);
    if (session.kind === "focus") {
      lastFocusMinutes.value = session.planned_minutes;
    }
    currentSession.value = null;
    stopTimer();
    await loadDay(selectedDate.value);
    pauseCards.value = await api.listPauseCards();
    await handleAfterStop(session);
  } catch (err) {
    showToast(err.message || "Erreur au stop");
  }
}

async function skipCurrent() {
  if (!currentSession.value) return;
  try {
    await api.skipSession(currentSession.value.id);
    currentSession.value = null;
    stopTimer();
    await loadDay(selectedDate.value);
  } catch (err) {
    showToast(err.message || "Erreur au skip");
  }
}

async function adjustCurrent(delta) {
  if (!currentSession.value) return;
  try {
    currentSession.value = await api.adjustSession(currentSession.value.id, { minutes_delta: delta });
    updateRemaining();
  } catch (err) {
    showToast(err.message || "Erreur ajustement");
  }
}

async function mergeNext() {
  if (!currentSession.value) return;
  try {
    currentSession.value = await api.mergeNext(currentSession.value.id);
    await loadDay(selectedDate.value);
  } catch (err) {
    showToast(err.message || "Impossible de coller");
  }
}

async function updateCurrentTask(taskId) {
  if (!currentSession.value) return;
  try {
    currentSession.value = await api.updateSession(currentSession.value.id, { task_id: taskId });
  } catch (err) {
    showToast("Impossible de changer la task");
  }
}

async function updateSessionNote({ id, note }) {
  try {
    await api.updateSession(id, { note });
    await loadDay(selectedDate.value);
  } catch (err) {
    showToast("Impossible de sauvegarder la note");
  }
}

async function addTask(payload) {
  try {
    await api.createTask(payload);
    tasks.value = await api.listTasks();
  } catch (err) {
    showToast("Impossible d'ajouter la task");
  }
}

async function updateTask(payload) {
  try {
    await api.updateTask(payload.id, payload);
    tasks.value = await api.listTasks();
  } catch (err) {
    showToast("Impossible de mettre a jour la task");
  }
}

async function toggleTaskStatus(task) {
  try {
    if (task.status === "done") {
      await api.updateTask(task.id, { status: "active" });
    } else {
      await api.completeTask(task.id);
    }
    tasks.value = await api.listTasks();
  } catch (err) {
    showToast("Impossible de changer le statut");
  }
}

async function saveSettings(payload) {
  try {
    settings.value = await api.updateSettings(payload);
    showToast("Settings enregistres");
  } catch (err) {
    showToast("Erreur settings");
  }
}

async function addPauseCard(payload) {
  try {
    await api.createPauseCard(payload);
    pauseCards.value = await api.listPauseCards();
  } catch (err) {
    showToast("Erreur creation carte");
  }
}

async function updatePauseCard(payload) {
  try {
    await api.updatePauseCard(payload.id, payload);
    pauseCards.value = await api.listPauseCards();
  } catch (err) {
    showToast("Erreur mise a jour carte");
  }
}

async function planSession(payload) {
  try {
    await api.planSession(payload);
    await loadDay(selectedDate.value);
  } catch (err) {
    showToast("Impossible de planifier");
  }
}

async function startPlanned(session) {
  try {
    if (isRunning.value) {
      showToast("Une session est deja en cours");
      return;
    }
    selectedDate.value = today();
    const started = await api.startPlannedSession(session.id);
    currentSession.value = started;
    await loadDay(selectedDate.value);
    startTimer();
  } catch (err) {
    showToast("Impossible de demarrer cette session");
  }
}

async function removePlanned(session) {
  try {
    await api.resetSession(session.id);
    await loadDay(selectedDate.value);
  } catch (err) {
    showToast("Impossible de supprimer");
  }
}

async function updatePlanned(payload) {
  try {
    await api.updateSession(payload.id, {
      title: payload.title,
      planned_time: payload.planned_time,
      planned_minutes: payload.planned_minutes,
      daypart_name: payload.daypart_name
    });
    await loadDay(selectedDate.value);
  } catch (err) {
    showToast("Impossible de mettre a jour la planification");
  }
}

async function consumePause(card) {
  if (card.remaining_today <= 0) {
    showToast("Carte indisponible");
    return;
  }
  try {
    const minutes = resolveBreakMinutes(lastFocusMinutes.value, settings.value?.default_break_minutes);
    const session = await api.consumePause({ pause_card_id: card.id, minutes });
    currentSession.value = session;
    showPauseModal.value = false;
    pauseCards.value = await api.listPauseCards();
    await loadDay(selectedDate.value);
    startTimer();
  } catch (err) {
    showToast(err.message || "Impossible de demarrer la pause");
  }
}

async function resetCurrentSession() {
  if (!currentSession.value) return;
  try {
    await api.resetSession(currentSession.value.id);
    currentSession.value = null;
    stopTimer();
    await loadDay(selectedDate.value);
  } catch (err) {
    showToast("Impossible de reset la session");
  }
}

async function resetDay(mode) {
  try {
    await api.resetDay(selectedDate.value, mode);
    await loadDay(selectedDate.value);
    pauseCards.value = await api.listPauseCards();
    lastFocusMinutes.value = null;
  } catch (err) {
    showToast("Impossible de reset le jour");
  }
}


async function moveSession({ session, daypart_name, date }) {
  try {
    await api.updateSession(session.id, { daypart_name, date });
    await loadDay(selectedDate.value);
  } catch (err) {
    showToast("Deplacement impossible");
  }
}

async function handleAfterStop(session) {
  if (session.kind === "focus") {
    showPauseModal.value = true;
  }
  await notifyEnd(session);
}

async function onSessionEnded() {
  if (!currentSession.value) return;
  await stopCurrent();
}

async function notifyEnd(session) {
  if (!settings.value?.notifications_enabled) {
    showToast("Session terminee");
    if (settings.value?.sound_enabled) playSound();
    return;
  }
  try {
    if (Notification.permission === "default") {
      await Notification.requestPermission();
    }
    if (Notification.permission === "granted") {
      new Notification("Tomate", { body: `Fin de ${session.kind}` });
    } else {
      showToast("Session terminee");
    }
  } catch (err) {
    showToast("Session terminee");
  }
  if (settings.value?.sound_enabled) playSound();
}

function playSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 520;
    gain.gain.value = 0.08;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.2);
  } catch (err) {
    return;
  }
}

function showToast(message) {
  toastMessage.value = message;
  setTimeout(() => {
    toastMessage.value = "";
  }, 3000);
}


function resolveBreakMinutes(focusMinutes, fallback) {
  if (!focusMinutes) return fallback || 5;
  if (focusMinutes >= 45) return 10;
  return 5;
}

onMounted(() => {
  loadAll().catch((err) => {
    showToast(err.message || "Erreur chargement");
  });
  clockId.value = setInterval(() => {
    currentTime.value = new Date();
  }, 1000);
});

onUnmounted(() => {
  if (clockId.value) {
    clearInterval(clockId.value);
  }
});

watch(selectedDate, (value) => {
  loadDay(value).catch((err) => {
    showToast(err.message || "Erreur chargement jour");
  });
});
</script>
