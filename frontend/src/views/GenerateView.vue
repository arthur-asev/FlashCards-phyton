<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { ArrowRight, Check, CircleAlert, LoaderCircle, Plus, Sparkles } from "@lucide/vue";

import { api, ApiError } from "../services/api";
import type { BackgroundJob, Deck, GeneratedCard, Subject, Topic } from "../types";

const subjects = ref<Subject[]>([]);
const topics = ref<Topic[]>([]);
const decks = ref<Deck[]>([]);
const form = ref({
  subject: "",
  topic: "",
  content: "",
  quantity: 5,
  difficulty: "medium",
  objective: "Revisar conceitos centrais",
  language: "pt-BR",
  deck_id: "",
});
const job = ref<BackgroundJob | null>(null);
const cards = ref<GeneratedCard[]>([]);
const busy = ref(false);
const errorMessage = ref("");
const noticeMessage = ref("");
const savedCards = ref<string[]>([]);
let pollTimer: number | undefined;

async function loadOptions() {
  try {
    const [subjectPage, deckPage] = await Promise.all([api.listSubjects(), api.listDecks()]);
    subjects.value = subjectPage.items;
    decks.value = deckPage.items;
    if (!form.value.subject && subjects.value.length) form.value.subject = subjects.value[0].name;
    if (!form.value.deck_id && decks.value.length) form.value.deck_id = decks.value[0].id;
    await loadTopics();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível carregar opções.";
  }
}

async function loadTopics() {
  const subject = subjects.value.find((item) => item.name === form.value.subject);
  topics.value = subject ? (await api.listTopics(subject.id)).items : [];
}

async function pollJob(jobId: string) {
  try {
    const current = await api.getJob(jobId);
    job.value = current;
    if (current.status === "COMPLETED") {
      cards.value = current.result?.cards ?? [];
      busy.value = false;
      return;
    }
    if (current.status === "FAILED" || current.status === "CANCELLED") {
      busy.value = false;
      errorMessage.value = current.error_message ?? "A geração não foi concluída.";
      return;
    }
    pollTimer = window.setTimeout(() => void pollJob(jobId), 900);
  } catch (error) {
    busy.value = false;
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível consultar o job.";
  }
}

async function generate() {
  errorMessage.value = "";
  noticeMessage.value = "";
  cards.value = [];
  savedCards.value = [];
  busy.value = true;
  try {
    const queued = await api.enqueueAIGeneration({
      ...form.value,
      deck_id: form.value.deck_id || null,
    });
    job.value = queued;
    await pollJob(queued.id);
  } catch (error) {
    busy.value = false;
    errorMessage.value = error instanceof ApiError ? error.message : "Não foi possível iniciar a geração.";
  }
}

async function retryGeneration() {
  if (!job.value) return;
  errorMessage.value = "";
  busy.value = true;
  try {
    const retried = await api.retryJob(job.value.id);
    job.value = retried;
    await pollJob(retried.id);
  } catch (error) {
    busy.value = false;
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível repetir o job.";
  }
}

async function saveCard(card: GeneratedCard, index: number) {
  if (!form.value.deck_id) return;
  try {
    const created = await api.createCard({
      deck_id: form.value.deck_id,
      topic_id: null,
      front: card.front,
      back: card.back,
      explanation: card.explanation ?? null,
      example: card.example ?? null,
      difficulty: card.difficulty ?? form.value.difficulty,
      source: card.source ?? `IA · ${job.value?.id ?? "geração"}`,
      tags: card.tags,
    });
    savedCards.value = [...savedCards.value, String(index)];
    noticeMessage.value = "Card adicionado ao deck.";
    window.setTimeout(() => (noticeMessage.value = ""), 2600);
    cards.value[index] = { ...card };
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível salvar o card.";
  }
}

onMounted(loadOptions);
onBeforeUnmount(() => {
  if (pollTimer !== undefined) window.clearTimeout(pollTimer);
});
</script>

<template>
  <section class="view-stack">
    <header class="page-heading">
      <div>
        <p class="eyebrow">ESTÚDIO</p>
        <h1>Gerar com IA</h1>
        <p class="heading-note">Geração em segundo plano <span class="dot-separator">/</span> revisão antes de salvar</p>
      </div>
      <div class="provider-pill"><span /> {{ job?.result?.provider ?? "MOCK / OPENAI" }}</div>
    </header>

    <p v-if="errorMessage" class="notice notice-error" role="alert"><CircleAlert :size="16" />{{ errorMessage }}</p>
    <p v-if="noticeMessage" class="notice notice-success" role="status"><Check :size="16" />{{ noticeMessage }}</p>

    <div class="generation-layout">
      <form class="generation-form" @submit.prevent="generate">
        <div class="form-block-title"><span>01</span><strong>Contexto</strong></div>
        <div class="form-columns">
          <label class="form-field">Matéria
            <input v-model="form.subject" list="subject-options" required maxlength="120" @change="loadTopics" />
            <datalist id="subject-options"><option v-for="subject in subjects" :key="subject.id" :value="subject.name" /></datalist>
          </label>
          <label class="form-field">Assunto
            <input v-model="form.topic" list="topic-options" required maxlength="120" />
            <datalist id="topic-options"><option v-for="topic in topics" :key="topic.id" :value="topic.name" /></datalist>
          </label>
        </div>
        <label class="form-field">Conteúdo-base
          <textarea v-model="form.content" required minlength="1" maxlength="20000" rows="8" placeholder="Cole o trecho ou anotações para transformar em cards." />
          <span class="field-meta">{{ form.content.length.toLocaleString("pt-BR") }} / 20.000</span>
        </label>

        <div class="form-block-title"><span>02</span><strong>Parâmetros</strong></div>
        <div class="form-columns form-four">
          <label class="form-field">Quantidade<input v-model.number="form.quantity" type="number" min="1" max="20" required /></label>
          <label class="form-field">Dificuldade<select v-model="form.difficulty"><option value="easy">Fácil</option><option value="medium">Média</option><option value="hard">Difícil</option></select></label>
          <label class="form-field">Idioma<select v-model="form.language"><option value="pt-BR">Português</option><option value="en">English</option><option value="es">Español</option></select></label>
          <label class="form-field">Salvar em<select v-model="form.deck_id"><option value="">Somente rascunho</option><option v-for="deck in decks" :key="deck.id" :value="deck.id">{{ deck.name }}</option></select></label>
        </div>
        <label class="form-field">Objetivo<input v-model="form.objective" maxlength="300" required /></label>
        <footer class="generation-footer">
          <span v-if="job" class="job-state"><span :class="`status-dot status-${job.status.toLowerCase()}`" />{{ job.status }} · {{ job.attempts }}/{{ job.max_attempts }}</span>
          <button class="button button-primary" type="submit" :disabled="busy || !form.content.trim()">
            <LoaderCircle v-if="busy" :size="16" class="spinning" aria-hidden="true" />
            <Sparkles v-else :size="16" aria-hidden="true" />
            {{ busy ? "Gerando…" : "Gerar cards" }} <ArrowRight v-if="!busy" :size="15" aria-hidden="true" />
          </button>
        </footer>
        <button v-if="job?.status === 'FAILED'" class="retry-link" type="button" :disabled="busy" @click="retryGeneration">Tentar novamente</button>
      </form>

      <section class="generation-results">
        <div class="results-heading">
          <p class="eyebrow">RESULTADO</p>
          <h2>{{ cards.length ? `${cards.length} cards gerados` : "Rascunhos" }}</h2>
        </div>
        <div v-if="busy" class="generation-wait">
          <div class="orbit-loader"><Sparkles :size="21" /></div>
          <strong>{{ job?.status === "PROCESSING" ? "Preparando seus cards" : "Na fila de geração" }}</strong>
          <span>O resultado aparece aqui ao concluir.</span>
        </div>
        <div v-else-if="cards.length" class="generated-list">
          <article v-for="(card, index) in cards" :key="`${job?.id}-${index}`" class="generated-card">
            <div class="generated-card-head"><span>RASCUNHO {{ String(index + 1).padStart(2, "0") }}</span><button v-if="form.deck_id" class="add-generated" type="button" :disabled="savedCards.includes(String(index))" @click="saveCard(card, index)"><Check v-if="savedCards.includes(String(index))" :size="14" /><Plus v-else :size="14" />{{ savedCards.includes(String(index)) ? "Adicionado" : "Adicionar ao deck" }}</button></div>
            <h3>{{ card.front }}</h3>
            <p>{{ card.back }}</p>
            <div v-if="card.explanation" class="generated-explanation">{{ card.explanation }}</div>
            <div class="generated-tags"><span v-for="tag in card.tags" :key="tag">{{ tag }}</span></div>
          </article>
        </div>
        <div v-else class="results-empty">
          <Sparkles :size="24" aria-hidden="true" />
          <strong>Nenhum rascunho ainda</strong>
          <span>Os cards gerados aparecem para revisão nesta área.</span>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.provider-pill { display: inline-flex; align-items: center; gap: 7px; padding: 7px 10px; border: 1px solid var(--line); border-radius: 5px; background: var(--surface); color: var(--muted); font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.04em; }
.provider-pill span { width: 6px; height: 6px; border-radius: 50%; background: var(--teal); }
.generation-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 0.85fr); gap: 18px; align-items: start; }
.generation-form { display: grid; gap: 15px; padding: 20px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }
.form-block-title { display: flex; align-items: center; gap: 9px; padding-bottom: 2px; color: var(--ink); font-size: 13px; }
.form-block-title span { color: var(--coral); font-family: var(--font-mono); font-size: 10px; }
.form-block-title strong { font-weight: 700; }
.form-four { grid-template-columns: 0.6fr 1fr 1fr 1.4fr; }
.field-meta { justify-self: end; color: var(--muted); font-family: var(--font-mono); font-size: 9px; }
.generation-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 3px; padding-top: 14px; border-top: 1px solid var(--line-soft); }
.job-state { display: inline-flex; align-items: center; gap: 7px; color: var(--muted); font-family: var(--font-mono); font-size: 10px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--gold); }
.status-completed { background: #318566; }
.status-failed { background: var(--coral); }
.status-processing { background: #3194a4; animation: pulse 1s infinite alternate; }
.retry-link { justify-self: end; border: 0; background: none; color: var(--coral); cursor: pointer; font-size: 11px; font-weight: 700; }
.generation-results { display: grid; gap: 12px; }
.results-heading { padding: 3px 2px 1px; }
.results-heading h2 { margin: 3px 0 0; font-family: var(--font-display); font-size: 22px; font-weight: 600; }
.results-empty, .generation-wait { display: grid; min-height: 260px; place-content: center; justify-items: center; gap: 10px; padding: 24px; border: 1px dashed var(--line-strong); border-radius: 8px; color: var(--teal); text-align: center; }
.results-empty strong, .generation-wait strong { color: var(--ink); font-size: 14px; }
.results-empty span, .generation-wait span { max-width: 240px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.orbit-loader { display: grid; width: 52px; height: 52px; place-items: center; border: 1px solid #b8d9ce; border-radius: 50%; background: #e8f3ee; animation: pulse 900ms infinite alternate; }
.generated-list { display: grid; gap: 10px; max-height: 700px; overflow: auto; }
.generated-card { padding: 15px 16px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); animation: slide-up 220ms ease-out both; }
.generated-card:nth-child(2) { animation-delay: 40ms; }
.generated-card:nth-child(3) { animation-delay: 80ms; }
.generated-card:nth-child(4) { animation-delay: 120ms; }
.generated-card-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: var(--coral); font-family: var(--font-mono); font-size: 9px; }
.generated-card h3 { margin: 13px 0 6px; font-family: var(--font-display); font-size: 16px; font-weight: 600; }
.generated-card > p { margin: 0; color: var(--ink-soft); font-size: 12px; line-height: 1.55; }
.generated-explanation { margin-top: 10px; padding: 9px 10px; border-left: 2px solid var(--gold); background: #fbf7ed; color: #67604d; font-size: 11px; line-height: 1.5; }
.generated-tags { display: flex; gap: 5px; margin-top: 11px; }
.generated-tags span { padding: 4px 6px; border-radius: 4px; background: var(--surface-tint); color: var(--muted); font-size: 9px; }
.add-generated { display: inline-flex; align-items: center; gap: 5px; padding: 5px 7px; border: 1px solid var(--line); border-radius: 4px; background: transparent; color: var(--teal); cursor: pointer; font-family: var(--font-sans); font-size: 10px; font-weight: 700; }
.add-generated:disabled { color: #42846c; background: #e8f3ee; cursor: default; }
.notice-error { display: flex; align-items: center; gap: 8px; }

@media (max-width: 900px) { .generation-layout { grid-template-columns: 1fr; } .generated-list { max-height: none; } }
@media (max-width: 620px) { .generation-form { padding: 16px; } .form-four { grid-template-columns: repeat(2, minmax(0, 1fr)); } .generation-footer { align-items: stretch; flex-direction: column; } .generation-footer .button { width: 100%; } }
</style>