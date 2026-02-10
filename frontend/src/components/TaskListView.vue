<template>
  <div class="panel stack">
    <div class="topbar">
      <h3>Tasks</h3>
      <div class="row">
        <button class="ghost" :class="{ active: filter === 'active' }" @click="filter = 'active'">Actives</button>
        <button class="ghost" :class="{ active: filter === 'done' }" @click="filter = 'done'">Terminees</button>
        <button class="ghost" :class="{ active: filter === 'all' }" @click="filter = 'all'">Toutes</button>
      </div>
    </div>
    <div class="cards">
      <div v-for="task in filteredTasks" :key="task.id" class="card">
        <input v-model="edits[task.id].title" class="input" />
        <div class="row">
          <input v-model.number="edits[task.id].estimate_pomodoros" class="input" type="number" min="1" />
          <button class="secondary" @click="toggleStatus(task)">
            {{ task.status === 'done' ? 'Reouvrir' : 'Terminer' }}
          </button>
        </div>
        <textarea v-model="edits[task.id].note" class="input" rows="2" placeholder="Note"></textarea>
        <div class="row">
          <button class="primary" @click="save(task.id)">Enregistrer</button>
        </div>
      </div>
      <div v-if="filteredTasks.length === 0" class="card">
        <small>Aucune task dans ce filtre.</small>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";

const props = defineProps({
  tasks: { type: Array, default: () => [] }
});

const emit = defineEmits(["update", "toggle-status"]);

const filter = ref("active");
const edits = reactive({});

watch(
  () => props.tasks,
  (value) => {
    value.forEach((task) => {
      edits[task.id] = {
        title: task.title,
        estimate_pomodoros: task.estimate_pomodoros,
        note: task.note || ""
      };
    });
  },
  { immediate: true }
);

const filteredTasks = computed(() => {
  if (filter.value === "all") return props.tasks;
  return props.tasks.filter((task) => task.status === filter.value);
});

function save(id) {
  emit("update", { id, ...edits[id] });
}

function toggleStatus(task) {
  emit("toggle-status", task);
}
</script>
