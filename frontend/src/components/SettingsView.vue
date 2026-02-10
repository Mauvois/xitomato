<template>
  <div class="panel stack">
    <div class="topbar">
      <div>
        <h3>Settings</h3>
      </div>
      <span v-if="firstRun" class="badge">Premier lancement</span>
    </div>

    <div class="settings-grid">
      <section class="settings-section">
        <div class="section-head">
          <h4>Demi-journees</h4>
          <small>3 creneaux ajustables pour la timeline et l'agenda.</small>
        </div>
        <div class="stack">
          <div class="daypart-card" v-for="(part, index) in localDayparts" :key="index">
            <input v-model="part.name" class="input" placeholder="Nom" />
            <div class="row">
              <label class="field">
                <span class="field-label">Debut</span>
                <input v-model="part.start" class="input" type="time" />
              </label>
              <label class="field">
                <span class="field-label">Fin</span>
                <input v-model="part.end" class="input" type="time" />
              </label>
            </div>
          </div>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-head">
          <h4>Notifications</h4>
          <small>Son discret et alertes navigateur.</small>
        </div>
        <div class="stack">
          <label class="toggle">
            <input type="checkbox" v-model="localSettings.notifications_enabled" />
            <span>Activer notifications</span>
          </label>
          <label class="toggle">
            <input type="checkbox" v-model="localSettings.sound_enabled" />
            <span>Activer son</span>
          </label>
        </div>
      </section>
    </div>

    <section class="settings-block pause-block">
      <div class="section-head">
        <h4>Cartes de pause</h4>
      </div>
      <div class="cards">
        <div v-for="card in pauseCards" :key="card.id" class="card">
          <strong>{{ card.name }}</strong>
          <small>Quota: {{ card.daily_quota }} / Jour</small>
          <div class="row">
            <label class="field">
              <span class="field-label">Quota</span>
              <input v-model.number="cardEdits[card.id].daily_quota" class="input" type="number" min="0" />
            </label>
            <label class="toggle">
              <input type="checkbox" v-model="cardEdits[card.id].is_joker" />
              <span>Joker</span>
            </label>
          </div>
          <button class="secondary" @click="updateCard(card.id)">Mettre a jour</button>
        </div>
      </div>

      <div class="card form-card">
        <strong>Nouvelle carte</strong>
        <div class="row">
          <label class="field">
            <span class="field-label">Nom</span>
            <input v-model="newCard.name" class="input" placeholder="Cafe" />
          </label>
          <label class="field">
            <span class="field-label">Quota</span>
            <input v-model.number="newCard.daily_quota" class="input" type="number" min="0" />
          </label>
          <label class="toggle">
            <input type="checkbox" v-model="newCard.is_joker" />
            <span>Joker</span>
          </label>
        </div>
        <button class="secondary" @click="addCard" :disabled="!newCard.name.trim()">Ajouter carte</button>
      </div>
    </section>

    <div class="row">
      <button class="primary" @click="save">Enregistrer</button>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";

const props = defineProps({
  settings: { type: Object, default: () => ({}) },
  pauseCards: { type: Array, default: () => [] },
  firstRun: { type: Boolean, default: false }
});

const emit = defineEmits(["save", "add-card", "update-card", "export"]);

const localSettings = reactive({
  default_focus_minutes: 45,
  default_break_minutes: 5,
  notifications_enabled: true,
  sound_enabled: true
});

const localDayparts = reactive([]);
const cardEdits = reactive({});

const newCard = reactive({
  name: "",
  daily_quota: 1,
  is_joker: false
});

watch(
  () => props.settings,
  (value) => {
    if (!value) return;
    localSettings.default_focus_minutes = value.default_focus_minutes ?? 45;
    localSettings.default_break_minutes = value.default_break_minutes ?? 5;
    localSettings.notifications_enabled = value.notifications_enabled ?? true;
    localSettings.sound_enabled = value.sound_enabled ?? true;
    localDayparts.splice(0, localDayparts.length, ...(value.dayparts || []));
  },
  { immediate: true }
);

watch(
  () => props.pauseCards,
  (value) => {
    value.forEach((card) => {
      cardEdits[card.id] = {
        name: card.name,
        daily_quota: card.daily_quota,
        is_joker: card.is_joker
      };
    });
  },
  { immediate: true }
);

function save() {
  emit("save", {
    dayparts: localDayparts,
    default_focus_minutes: localSettings.default_focus_minutes,
    default_break_minutes: localSettings.default_break_minutes,
    notifications_enabled: localSettings.notifications_enabled,
    sound_enabled: localSettings.sound_enabled
  });
}

function addCard() {
  emit("add-card", { ...newCard });
  newCard.name = "";
  newCard.daily_quota = 1;
  newCard.is_joker = false;
}

function updateCard(id) {
  emit("update-card", { id, ...cardEdits[id] });
}
</script>
