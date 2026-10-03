<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { BookPlus, ChevronLeft, ChevronRight, Layers3, Pencil, Plus, Search, Tag, Trash2, X } from "@lucide/vue";

import { api, ApiError } from "../services/api";
import type { Deck, Flashcard, Subject, Topic } from "../types";

const props = defineProps<{ newCardRequest: number }>();

const decks = ref<Deck[]>([]);
const subjects = ref<Subject[]>([]);
const topics = ref<Topic[]>([]);
const cards = ref<Flashcard[]>([]);
const selectedDeckId = ref("");
const cardSearch = ref("");
const currentPage = ref(1);
const totalCards = ref(0);
const pageSize = 20;
const busy = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const modal = ref<"deck" | "card" | "subject" | null>(null);
const editingDeckId = ref("");
const editingCardId = ref("");

const deckForm = ref({ name: "", description: "", subject_id: "" });
const cardForm = ref({
  deck_id: "",
  topic_id: "",
  front: "",
  back: "",
  explanation: "",
  example: "",
  difficulty: "medium",
  source: "",
  tags: "",
});
const subjectName = ref("");
const selectedDeck = computed(() => decks.value.find((deck) => deck.id === selectedDeckId.value) ?? null);
const selectedSubjectLabel = computed(() => {
  const subjectId = selectedDeck.value?.subject_id;
  if (!subjectId) return "DECK";
  return subjects.value.find((subject) => subject.id === subjectId)?.name ?? "MATÉRIA";
});
const totalPages = computed(() => Math.max(1, Math.ceil(totalCards.value / pageSize)));

async function loadDecks() {
  const [deckPage, subjectPage] = await Promise.all([api.listDecks(), api.listSubjects()]);
  decks.value = deckPage.items;
  subjects.value = subjectPage.items;
  if (!selectedDeckId.value && decks.value.length) selectedDeckId.value = decks.value[0].id;
  if (selectedDeckId.value && !decks.value.some((deck) => deck.id === selectedDeckId.value)) {
    selectedDeckId.value = decks.value[0]?.id ?? "";
  }
}

async function loadCards() {
  if (!selectedDeckId.value) {
    cards.value = [];
    totalCards.value = 0;
    return;
  }
  const result = await api.listCards({
    deck_id: selectedDeckId.value,
    search: cardSearch.value.trim() || undefined,
    page: currentPage.value,
    page_size: pageSize,
  });
  cards.value = result.items;
  totalCards.value = result.total;
}

async function refreshLibrary() {
  busy.value = true;
  errorMessage.value = "";
  try {
    await loadDecks();
    await loadCards();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível carregar a biblioteca.";
  } finally {
    busy.value = false;
  }
}

onMounted(refreshLibrary);
watch(
  () => props.newCardRequest,
  (requestNumber, previousRequestNumber) => {
    if (requestNumber <= previousRequestNumber) return;
    if (selectedDeckId.value) openCardForm();
    else openDeckForm();
  },
);
watch(selectedDeckId, () => {
  currentPage.value = 1;
  loadCards().catch((error: unknown) => {
    errorMessage.value = error instanceof Error ? error.message : "Falha ao carregar cards.";
  });
});

function openDeckForm(deck?: Deck) {
  editingDeckId.value = deck?.id ?? "";
  deckForm.value = {
    name: deck?.name ?? "",
    description: deck?.description ?? "",
    subject_id: deck?.subject_id ?? "",
  };
  errorMessage.value = "";
  modal.value = "deck";
}

async function saveDeck() {
  busy.value = true;
  errorMessage.value = "";
  try {
    const payload = {
      name: deckForm.value.name,
      description: deckForm.value.description || "",
      subject_id: deckForm.value.subject_id || null,
    };
    const result = editingDeckId.value
      ? await api.updateDeck(editingDeckId.value, payload)
      : await api.createDeck(payload);
    selectedDeckId.value = result.id;
    modal.value = null;
    successMessage.value = editingDeckId.value ? "Deck atualizado." : "Deck criado.";
    await refreshLibrary();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Não foi possível salvar o deck.";
  } finally {
    busy.value = false;
  }
}

async function deleteDeck(deck: Deck) {
  if (!window.confirm(`Excluir o deck “${deck.name}” e seus cards?`)) return;
  errorMessage.value = "";
  try {
    await api.deleteDeck(deck.id);
    if (selectedDeckId.value === deck.id) selectedDeckId.value = "";
    successMessage.value = "Deck excluído.";
    await refreshLibrary();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Não foi possível excluir o deck.";
  }
}

async function openCardForm(card?: Flashcard) {
  editingCardId.value = card?.id ?? "";
  const deckId = card?.deck_id ?? selectedDeckId.value;
  cardForm.value = {
    deck_id: deckId,
    topic_id: card?.topic_id ?? "",
    front: card?.front ?? "",
    back: card?.back ?? "",
    explanation: card?.explanation ?? "",
    example: card?.example ?? "",
    difficulty: card?.difficulty ?? "medium",
    source: card?.source ?? "",
    tags: card?.tags.join(", ") ?? "",
  };
  errorMessage.value = "";
  modal.value = "card";
  await loadTopicsForDeck(deckId);
}

async function loadTopicsForDeck(deckId: string) {
  const deck = decks.value.find((item) => item.id === deckId);
  topics.value = deck?.subject_id ? (await api.listTopics(deck.subject_id)).items : [];
}

async function changeCardDeck(event: Event) {
  cardForm.value.deck_id = (event.target as HTMLSelectElement).value;
  cardForm.value.topic_id = "";
  await loadTopicsForDeck(cardForm.value.deck_id);
}

async function saveCard() {
  busy.value = true;
  errorMessage.value = "";
  const payload = {
    deck_id: cardForm.value.deck_id,
    topic_id: cardForm.value.topic_id || null,
    front: cardForm.value.front,
    back: cardForm.value.back,
    explanation: cardForm.value.explanation || null,
    example: cardForm.value.example || null,
    difficulty: cardForm.value.difficulty || null,
    source: cardForm.value.source || null,
    tags: cardForm.value.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
  };
  try {
    if (editingCardId.value) await api.updateCard(editingCardId.value, payload);
    else await api.createCard(payload);
    modal.value = null;
    selectedDeckId.value = cardForm.value.deck_id;
    currentPage.value = 1;
    successMessage.value = editingCardId.value ? "Card atualizado." : "Card criado.";
    await loadCards();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Não foi possível salvar o card.";
  } finally {
    busy.value = false;
  }
}

async function deleteCard(card: Flashcard) {
  if (!window.confirm("Excluir este card?")) return;
  try {
    await api.deleteCard(card.id);
    successMessage.value = "Card excluído.";
    await loadCards();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Não foi possível excluir o card.";
  }
}

async function createSubject() {
  busy.value = true;
  errorMessage.value = "";
  try {
    const subject = await api.createSubject(subjectName.value);
    subjects.value = [...subjects.value, subject].sort((left, right) => left.name.localeCompare(right.name));
    deckForm.value.subject_id = subject.id;
    subjectName.value = "";
    modal.value = "deck";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível criar a matéria.";
  } finally {
    busy.value = false;
  }
}

async function goToPage(page: number) {
  currentPage.value = page;
  await loadCards();
}
</script>

<template>
  <section class="view-stack">
    <header class="page-heading">
      <div>
        <p class="eyebrow">ACERVO</p>
        <h1>Biblioteca</h1>
        <p class="heading-note">{{ decks.length }} decks <span class="dot-separator">/</span> {{ totalCards }} cards</p>
      </div>
      <div class="heading-actions">
        <button class="button button-outline" type="button" @click="openDeckForm()">
          <Layers3 :size="16" aria-hidden="true" /> Novo deck
        </button>
        <button class="button button-primary" type="button" :disabled="!decks.length" @click="openCardForm()">
          <BookPlus :size="16" aria-hidden="true" /> Novo card
        </button>
      </div>
    </header>

    <p v-if="errorMessage" class="notice notice-error" role="alert">{{ errorMessage }}</p>
    <p v-if="successMessage" class="notice notice-success" role="status">{{ successMessage }}</p>

    <div class="library-layout">
      <aside class="deck-rail">
        <div class="rail-heading"><span>DECKS</span><button type="button" aria-label="Criar deck" @click="openDeckForm()"><Plus :size="16" /></button></div>
        <button
          v-for="deck in decks"
          :key="deck.id"
          type="button"
          class="deck-choice"
          :class="{ selected: selectedDeckId === deck.id }"
          @click="selectedDeckId = deck.id"
        >
          <span class="deck-color" />
          <span class="deck-choice-text"><strong>{{ deck.name }}</strong><small>{{ deck.description || "Sem descrição" }}</small></span>
          <span class="deck-menu" @click.stop>
            <button type="button" :aria-label="`Editar ${deck.name}`" @click="openDeckForm(deck)"><Pencil :size="14" /></button>
            <button type="button" :aria-label="`Excluir ${deck.name}`" @click="deleteDeck(deck)"><Trash2 :size="14" /></button>
          </span>
        </button>
        <button v-if="selectedDeck" class="rail-add" type="button" @click="openCardForm()"><Plus :size="14" /> Adicionar card</button>
      </aside>

      <section class="card-library">
        <div class="library-toolbar">
          <div class="selected-deck-heading">
            <p class="eyebrow">{{ selectedSubjectLabel }}</p>
            <h2>{{ selectedDeck?.name ?? "Selecione um deck" }}</h2>
          </div>
          <label class="search-field">
            <Search :size="16" aria-hidden="true" />
            <input v-model="cardSearch" type="search" placeholder="Buscar cards" @keydown.enter="currentPage = 1; loadCards()" />
            <button type="button" aria-label="Buscar" @click="currentPage = 1; loadCards()">↵</button>
          </label>
        </div>

        <div v-if="busy" class="library-loading">Carregando acervo…</div>
        <div v-else-if="cards.length" class="card-list">
          <article v-for="card in cards" :key="card.id" class="library-card">
            <div class="card-copy">
              <span class="card-kicker">{{ card.difficulty || "CARD" }} <span v-if="card.topic_id">· {{ topics.find((topic) => topic.id === card.topic_id)?.name }}</span></span>
              <h3>{{ card.front }}</h3>
              <p>{{ card.back }}</p>
              <div class="tag-row"><span v-for="tag in card.tags" :key="tag"><Tag :size="11" />{{ tag }}</span></div>
            </div>
            <div class="card-actions">
              <button type="button" :aria-label="`Editar ${card.front}`" @click="openCardForm(card)"><Pencil :size="15" /></button>
              <button type="button" :aria-label="`Excluir ${card.front}`" @click="deleteCard(card)"><Trash2 :size="15" /></button>
            </div>
          </article>
        </div>
        <div v-else class="library-empty">
          <Layers3 :size="27" aria-hidden="true" />
          <strong>{{ selectedDeck ? "Este deck está vazio" : "Sua biblioteca começa aqui" }}</strong>
          <p>{{ selectedDeck ? "Adicione seu primeiro card." : "Crie um deck para organizar seus cards." }}</p>
          <button v-if="selectedDeck" class="button button-primary" type="button" @click="openCardForm()"><Plus :size="15" /> Novo card</button>
          <button v-else class="button button-primary" type="button" @click="openDeckForm()"><Plus :size="15" /> Novo deck</button>
        </div>

        <footer v-if="totalCards" class="pagination-bar">
          <span>{{ totalCards }} cards · página {{ currentPage }} de {{ totalPages }}</span>
          <div>
            <button type="button" aria-label="Página anterior" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)"><ChevronLeft :size="16" /></button>
            <button type="button" aria-label="Próxima página" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)"><ChevronRight :size="16" /></button>
          </div>
        </footer>
      </section>
    </div>

    <div v-if="modal" class="modal-backdrop" @click.self="modal = null">
      <form v-if="modal === 'deck'" class="edit-dialog" @submit.prevent="saveDeck">
        <header><div><p class="eyebrow">ORGANIZAÇÃO</p><h2>{{ editingDeckId ? "Editar deck" : "Novo deck" }}</h2></div><button type="button" class="icon-button" aria-label="Fechar" @click="modal = null"><X :size="18" /></button></header>
        <label class="form-field">Nome<input v-model="deckForm.name" required maxlength="160" autofocus /></label>
        <label class="form-field">Descrição<textarea v-model="deckForm.description" rows="3" maxlength="2000" /></label>
        <label class="form-field">Matéria
          <select v-model="deckForm.subject_id"><option value="">Sem matéria</option><option v-for="subject in subjects" :key="subject.id" :value="subject.id">{{ subject.name }}</option></select>
        </label>
        <button type="button" class="text-link form-inline-action" @click="modal = 'subject'">+ Criar matéria</button>
        <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>
        <footer><button class="button button-quiet" type="button" @click="modal = null">Cancelar</button><button class="button button-primary" type="submit" :disabled="busy">{{ busy ? "Salvando…" : "Salvar deck" }}</button></footer>
      </form>

      <form v-else-if="modal === 'card'" class="edit-dialog card-dialog" @submit.prevent="saveCard">
        <header><div><p class="eyebrow">BIBLIOTECA</p><h2>{{ editingCardId ? "Editar card" : "Novo card" }}</h2></div><button type="button" class="icon-button" aria-label="Fechar" @click="modal = null"><X :size="18" /></button></header>
        <label class="form-field">Deck<select :value="cardForm.deck_id" required @change="changeCardDeck"><option v-for="deck in decks" :key="deck.id" :value="deck.id">{{ deck.name }}</option></select></label>
        <div class="form-columns">
          <label class="form-field">Frente<textarea v-model="cardForm.front" required rows="3" maxlength="10000" /></label>
          <label class="form-field">Verso<textarea v-model="cardForm.back" required rows="3" maxlength="10000" /></label>
        </div>
        <div class="form-columns">
          <label class="form-field">Explicação<textarea v-model="cardForm.explanation" rows="2" maxlength="10000" /></label>
          <label class="form-field">Exemplo<textarea v-model="cardForm.example" rows="2" maxlength="10000" /></label>
        </div>
        <div class="form-columns form-three">
          <label class="form-field">Assunto<select v-model="cardForm.topic_id"><option value="">Sem assunto</option><option v-for="topic in topics" :key="topic.id" :value="topic.id">{{ topic.name }}</option></select></label>
          <label class="form-field">Dificuldade<select v-model="cardForm.difficulty"><option value="easy">Fácil</option><option value="medium">Média</option><option value="hard">Difícil</option></select></label>
          <label class="form-field">Origem<input v-model="cardForm.source" maxlength="500" /></label>
        </div>
        <label class="form-field">Tags<input v-model="cardForm.tags" placeholder="biologia, prova" /></label>
        <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>
        <footer><button class="button button-quiet" type="button" @click="modal = null">Cancelar</button><button class="button button-primary" type="submit" :disabled="busy">{{ busy ? "Salvando…" : "Salvar card" }}</button></footer>
      </form>

      <form v-else class="edit-dialog compact-dialog" @submit.prevent="createSubject">
        <header><div><p class="eyebrow">BIBLIOTECA</p><h2>Nova matéria</h2></div><button type="button" class="icon-button" aria-label="Fechar" @click="modal = 'deck'"><X :size="18" /></button></header>
        <label class="form-field">Nome<input v-model="subjectName" required maxlength="120" autofocus /></label>
        <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>
        <footer><button class="button button-quiet" type="button" @click="modal = 'deck'">Voltar</button><button class="button button-primary" type="submit" :disabled="busy">Criar matéria</button></footer>
      </form>
    </div>
  </section>
</template>

<style scoped>
.heading-actions {
  display: flex;
  gap: 9px;
}

.library-layout {
  display: grid;
  grid-template-columns: minmax(210px, 0.28fr) minmax(0, 1fr);
  gap: 17px;
  align-items: start;
}

.deck-rail,
.card-library {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.deck-rail {
  overflow: hidden;
  padding: 10px;
}

.rail-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px 10px;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
}

.rail-heading button,
.deck-menu button,
.card-actions button,
.pagination-bar button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.rail-heading button:hover,
.deck-menu button:hover,
.card-actions button:hover,
.pagination-bar button:hover:not(:disabled) {
  background: var(--surface-tint);
  color: var(--teal);
}

.deck-choice {
  display: grid;
  width: 100%;
  grid-template-columns: 5px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 11px 8px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
}

.deck-choice:hover,
.deck-choice.selected {
  background: #eef4f0;
}

.deck-color {
  width: 4px;
  height: 30px;
  border-radius: 4px;
  background: var(--teal);
}

.deck-choice:nth-of-type(3n) .deck-color { background: var(--coral); }
.deck-choice:nth-of-type(4n) .deck-color { background: var(--gold); }

.deck-choice-text {
  display: grid;
  min-width: 0;
  gap: 4px;
}

.deck-choice-text strong,
.deck-choice-text small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deck-choice-text strong { font-size: 12px; }
.deck-choice-text small { color: var(--muted); font-size: 10px; }

.deck-menu {
  display: flex;
  opacity: 0;
  transition: opacity 120ms ease;
}

.deck-choice:hover .deck-menu,
.deck-choice.selected .deck-menu { opacity: 1; }

.rail-add {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 10px 8px 5px;
  padding: 5px 0;
  border: 0;
  background: transparent;
  color: var(--teal);
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
}

.card-library { min-width: 0; overflow: hidden; }

.library-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 18px;
  border-bottom: 1px solid var(--line);
}

.selected-deck-heading h2 {
  margin: 3px 0 0;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 600;
}

.search-field {
  display: flex;
  width: min(270px, 50%);
  align-items: center;
  gap: 8px;
  padding: 0 8px 0 11px;
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--muted);
}

.search-field input {
  min-width: 0;
  height: 36px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  font-size: 11px;
}

.search-field input:focus { outline: none; box-shadow: none; }
.search-field button { border: 0; background: none; color: var(--muted); cursor: pointer; }

.library-loading,
.library-empty {
  display: grid;
  min-height: 270px;
  place-content: center;
  justify-items: center;
  gap: 11px;
  color: var(--muted);
  text-align: center;
}

.library-empty svg { color: var(--teal); }
.library-empty strong { color: var(--ink); font-family: var(--font-display); font-size: 18px; }
.library-empty p { margin: 0 0 4px; font-size: 12px; }

.library-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 13px;
  padding: 17px 18px;
  border-bottom: 1px solid var(--line-soft);
}

.library-card:last-child { border-bottom: 0; }
.card-copy { min-width: 0; }
.card-kicker { color: var(--coral); font-family: var(--font-mono); font-size: 9px; text-transform: uppercase; }
.card-copy h3 { margin: 6px 0 4px; font-size: 13px; font-weight: 700; }
.card-copy p { margin: 0; color: var(--muted); font-size: 12px; }

.tag-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 11px; }
.tag-row span { display: inline-flex; align-items: center; gap: 4px; padding: 4px 6px; border-radius: 4px; background: #f0f4f1; color: #52655d; font-size: 9px; }
.card-actions { display: flex; align-items: flex-start; opacity: 0.65; }
.card-actions:hover { opacity: 1; }

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 14px;
  border-top: 1px solid var(--line);
  color: var(--muted);
  font-size: 10px;
}

.pagination-bar div { display: flex; gap: 4px; }
.pagination-bar button:disabled { cursor: not-allowed; opacity: 0.35; }

.modal-backdrop {
  position: fixed;
  z-index: 20;
  inset: 0;
  display: grid;
  place-items: center;
  overflow: auto;
  padding: 20px;
  background: rgba(11, 31, 28, 0.52);
  animation: fade-in 130ms ease-out;
}

.edit-dialog {
  display: grid;
  width: min(520px, 100%);
  max-height: min(90vh, 820px);
  gap: 15px;
  overflow: auto;
  padding: 22px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: 0 24px 80px rgba(8, 30, 25, 0.22);
}

.card-dialog { width: min(740px, 100%); }
.compact-dialog { width: min(430px, 100%); }
.edit-dialog header { display: flex; align-items: flex-start; justify-content: space-between; }
.edit-dialog header h2 { margin: 3px 0 0; font-family: var(--font-display); font-size: 23px; }
.form-inline-action { justify-self: start; }
.form-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.form-three { grid-template-columns: 1fr 1fr 1fr; }
.edit-dialog footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 3px; }
.inline-error { margin: 0; color: #a83f32; font-size: 12px; }

@media (max-width: 900px) {
  .library-layout { grid-template-columns: 1fr; }
  .deck-rail { display: flex; overflow-x: auto; align-items: center; gap: 5px; }
  .rail-heading { flex: 0 0 auto; }
  .deck-choice { width: auto; min-width: 170px; }
  .rail-add { flex: 0 0 auto; }
  .deck-menu { opacity: 1; }
}

@media (max-width: 620px) {
  .heading-actions { width: 100%; }
  .heading-actions .button { flex: 1; }
  .library-toolbar { align-items: stretch; flex-direction: column; }
  .search-field { width: 100%; }
  .form-columns, .form-three { grid-template-columns: 1fr; }
  .edit-dialog { padding: 18px; }
}
</style>