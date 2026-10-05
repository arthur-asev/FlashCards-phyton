<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ArrowLeft, ArrowRight, Check, RotateCcw, Sparkles } from "@lucide/vue";
import MultiSelect from "primevue/multiselect";
import Select from "primevue/select";

import { api, ApiError } from "../services/api";
import type { Deck, Flashcard, ReviewStats, Topic } from "../types";

type DueCard = Flashcard & { next_review_at: string | null };

const cards = ref<DueCard[]>([]);
const stats = ref<ReviewStats | null>(null);
const decks = ref<Deck[]>([]);
const topics = ref<Topic[]>([]);
const selectedDeckId = ref("");
const selectedTopicIds = ref<string[]>([]);
const activeIndex = ref(0);
const showBack = ref(false);
const busy = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const activeCard = computed(() => cards.value[activeIndex.value] ?? null);
const progress = computed(() => (cards.value.length ? Math.round((activeIndex.value / cards.value.length) * 100) : 0));

async function loadQueue() {
  busy.value = true;
  errorMessage.value = "";
  try {
    const [due, reviewStats] = await Promise.all([
      api.getDueCards(100, { deck_id: selectedDeckId.value || undefined, topic_ids: selectedTopicIds.value }),
      api.getReviewStats(),
    ]);
    cards.value = due.items;
    stats.value = reviewStats;
    activeIndex.value = 0;
    showBack.value = false;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível carregar a revisão.";
  } finally {
    busy.value = false;
  }
}

async function loadTopics() {
  const deck = decks.value.find((item) => item.id === selectedDeckId.value);
  topics.value = deck?.subject_id ? (await api.listTopics(deck.subject_id)).items : [];
  selectedTopicIds.value = selectedTopicIds.value.filter((id) => topics.value.some((topic) => topic.id === id));
}

function setSelectedTopics(value: string[] | null) {
  selectedTopicIds.value = value ?? [];
}

watch(selectedDeckId, async () => {
  await loadTopics();
  await loadQueue();
});
watch(selectedTopicIds, loadQueue);

async function rateCard(rating: number) {
  if (!activeCard.value) return;
  busy.value = true;
  errorMessage.value = "";
  try {
    await api.submitReview(activeCard.value.id, rating);
    cards.value.splice(activeIndex.value, 1);
    if (activeIndex.value >= cards.value.length) activeIndex.value = Math.max(0, cards.value.length - 1);
    showBack.value = false;
    stats.value = await api.getReviewStats();
    successMessage.value = "Avaliação registrada.";
    window.setTimeout(() => (successMessage.value = ""), 1800);
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Não foi possível salvar a avaliação.";
  } finally {
    busy.value = false;
  }
}

function moveCard(direction: -1 | 1) {
  if (!cards.value.length) return;
  activeIndex.value = (activeIndex.value + direction + cards.value.length) % cards.value.length;
  showBack.value = false;
}

onMounted(async () => {
  try {
    decks.value = (await api.listDecks()).items;
    await loadTopics();
    await loadQueue();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível carregar decks e categorias.";
  }
});
</script>

<template>
  <section class="view-stack">
    <header class="page-heading">
      <div>
        <p class="eyebrow">SESSÃO DE ESTUDO</p>
        <h1>Revisar cards</h1>
        <p class="heading-note">{{ cards.length }} para revisar nesta seleção <span class="dot-separator">/</span> {{ stats?.total_reviews ?? 0 }} avaliações registradas</p>
      </div>
      <div class="review-filters">
        <label>Deck
          <Select v-model="selectedDeckId" :options="[{ id: '', name: 'Todos os decks' }, ...decks]" option-label="name" option-value="id" aria-label="Filtrar por deck" class="review-deck-select" />
        </label>
        <label>Categoria
          <MultiSelect
            v-model="selectedTopicIds"
            @update:model-value="setSelectedTopics"
            :options="topics"
            option-label="name"
            option-value="id"
            :disabled="!topics.length"
            :placeholder="topics.length ? 'Todas as categorias' : 'Selecione um deck primeiro'"
            :max-selected-labels="2"
            selected-items-label="{0} categorias selecionadas"
            empty-filter-message="Nenhuma categoria encontrada"
            empty-message="Nenhuma categoria disponível"
            filter
            show-clear
            display="chip"
            aria-label="Selecionar categorias da revisão"
            class="review-category-select"
          />
        </label>
        <button class="button button-quiet" type="button" :disabled="busy" @click="loadQueue"><RotateCcw :size="15" /> Atualizar fila</button>
      </div>
    </header>

    <p v-if="errorMessage" class="notice notice-error" role="alert">{{ errorMessage }}</p>
    <p v-if="successMessage" class="notice notice-success" role="status"><Check :size="15" /> {{ successMessage }}</p>

    <div v-if="busy && !activeCard" class="review-empty">Carregando fila…</div>
    <section v-else-if="activeCard" class="review-session">
      <div class="session-topline">
        <span class="session-count">{{ String(activeIndex + 1).padStart(2, "0") }} <i>/</i> {{ String(cards.length).padStart(2, "0") }}</span>
        <div class="progress-track"><span :style="{ width: `${progress}%` }" /></div>
        <span class="session-difficulty">{{ activeCard.difficulty || "GERAL" }}</span>
      </div>

      <article class="study-card" :class="{ flipped: showBack }" @click="showBack = !showBack">
        <div class="study-card-meta"><span>{{ showBack ? "VERSO" : "FRENTE" }}</span><span>{{ activeCard.tags.join(" · ") || "CARD" }}</span></div>
        <div class="study-card-content">
          <p>{{ showBack ? activeCard.back : activeCard.front }}</p>
          <div v-if="showBack && activeCard.explanation" class="study-explanation">{{ activeCard.explanation }}</div>
          <div v-if="showBack && activeCard.example" class="study-example"><span>EXEMPLO</span>{{ activeCard.example }}</div>
        </div>
        <button type="button" class="flip-hint" @click.stop="showBack = !showBack">
          <span>{{ showBack ? "Ver frente" : "Revelar resposta" }}</span><Sparkles :size="15" aria-hidden="true" />
        </button>
      </article>

      <div v-if="showBack" class="rating-area">
        <p>Como foi?</p>
        <div class="rating-grid">
          <button v-for="rating in [0, 1, 2, 3, 4, 5]" :key="rating" type="button" :disabled="busy" :class="`rating rating-${rating}`" @click="rateCard(rating)">
            <strong>{{ rating }}</strong><span>{{ ["De novo", "Difícil", "Difícil", "Regular", "Bom", "Fácil"][rating] }}</span>
          </button>
        </div>
      </div>

      <div class="session-navigation">
        <button type="button" class="button button-quiet" :disabled="cards.length < 2" @click="moveCard(-1)"><ArrowLeft :size="15" /> Anterior</button>
        <button type="button" class="button button-quiet" :disabled="cards.length < 2" @click="moveCard(1)">Próximo <ArrowRight :size="15" /></button>
      </div>
    </section>
    <section v-else class="review-empty">
      <span class="empty-check"><Check :size="22" /></span>
      <strong>Fila concluída</strong>
      <p>Não há cards vencidos para revisar.</p>
      <button class="button button-outline" type="button" @click="loadQueue"><RotateCcw :size="15" /> Conferir novamente</button>
    </section>
  </section>
</template>

<style scoped>
.review-session { width: min(760px, 100%); margin: 0 auto; }
.review-filters { display: flex; align-items: end; gap: 10px; }
.review-filters label { display: grid; min-width: 180px; gap: 4px; color: var(--muted); font-size: 10px; }
.review-filters :deep(.p-select), .review-filters :deep(.p-multiselect) { width: 100%; min-height: 37px; border-color: var(--line-strong); border-radius: 5px; background: var(--surface); color: var(--ink); font-family: var(--font-sans); font-size: 12px; }
.review-filters :deep(.p-select-label), .review-filters :deep(.p-multiselect-label) { padding: 8px 10px; }
.review-filters :deep(.p-multiselect-label) { display: flex; flex-wrap: wrap; gap: 4px; }
.review-filters :deep(.p-multiselect-chip) { border-radius: 4px; background: #e8f3ee; color: var(--teal-dark); font-size: 10px; }
.review-filters :deep(.p-select-dropdown), .review-filters :deep(.p-multiselect-dropdown) { width: 32px; }
.session-topline { display: grid; grid-template-columns: 55px minmax(0, 1fr) 70px; align-items: center; gap: 12px; margin-bottom: 12px; }
.session-count { color: var(--ink); font-family: var(--font-mono); font-size: 11px; }
.session-count i { padding: 0 3px; color: var(--muted); font-style: normal; }
.progress-track { height: 4px; overflow: hidden; border-radius: 5px; background: #dce5df; }
.progress-track span { display: block; height: 100%; border-radius: inherit; background: var(--coral); transition: width 200ms ease; }
.session-difficulty { justify-self: end; color: var(--muted); font-family: var(--font-mono); font-size: 9px; }
.study-card { display: flex; min-height: 345px; flex-direction: column; justify-content: space-between; padding: 22px 25px; border: 1px solid #c8d7cf; border-radius: 8px; background: var(--surface); cursor: pointer; box-shadow: 0 10px 25px rgba(17, 52, 43, 0.045); transition: border-color 150ms ease, transform 150ms ease; }
.study-card:hover { border-color: var(--teal); transform: translateY(-1px); }
.study-card.flipped { border-color: #e0c27e; background: #fffdf8; }
.study-card-meta { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-family: var(--font-mono); font-size: 9px; }
.study-card-meta span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.study-card-content { display: grid; align-content: center; justify-items: center; gap: 14px; min-height: 220px; padding: 22px 6%; text-align: center; }
.study-card-content > p { margin: 0; color: var(--ink); font-family: var(--font-display); font-size: 26px; font-weight: 550; line-height: 1.35; }
.study-explanation { max-width: 520px; color: var(--muted); font-size: 13px; line-height: 1.6; }
.study-example { display: flex; max-width: 520px; gap: 9px; color: var(--ink-soft); font-size: 12px; }
.study-example span { color: var(--coral); font-family: var(--font-mono); font-size: 9px; }
.flip-hint { display: inline-flex; align-self: center; align-items: center; gap: 8px; border: 0; background: transparent; color: var(--teal); cursor: pointer; font-size: 11px; font-weight: 700; }
.rating-area { margin-top: 19px; }
.rating-area > p { margin: 0 0 10px; color: var(--muted); font-size: 11px; text-align: center; }
.rating-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; }
.rating { display: grid; min-height: 58px; place-content: center; gap: 3px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--ink); cursor: pointer; transition: border-color 120ms ease, background 120ms ease; }
.rating:hover:not(:disabled) { border-color: var(--teal); background: #edf5f1; }
.rating strong { font-family: var(--font-display); font-size: 17px; }
.rating span { color: var(--muted); font-size: 9px; }
.rating-0:hover:not(:disabled), .rating-1:hover:not(:disabled) { border-color: var(--coral); background: #fff0ec; }
.rating-5:hover:not(:disabled) { border-color: var(--gold); background: #fff8e8; }
.rating:disabled { opacity: 0.6; cursor: wait; }
.session-navigation { display: flex; justify-content: space-between; margin-top: 17px; }
.review-empty { display: grid; min-height: 320px; place-content: center; justify-items: center; gap: 10px; border: 1px dashed var(--line-strong); border-radius: 8px; color: var(--muted); text-align: center; }
.review-empty strong { color: var(--ink); font-family: var(--font-display); font-size: 20px; }
.review-empty p { margin: 0 0 7px; font-size: 12px; }
.empty-check { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 50%; background: #e8f3ee; color: var(--teal); }
.notice-success, .notice-error { display: flex; align-items: center; gap: 8px; }

@media (max-width: 620px) {
  .review-filters { flex-wrap: wrap; align-items: stretch; }
  .review-filters label { flex: 1 1 190px; }
  .study-card { min-height: 310px; padding: 17px; }
  .study-card-content > p { font-size: 21px; }
  .rating-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .session-topline { grid-template-columns: 46px minmax(0, 1fr) 56px; gap: 7px; }
}
</style>
