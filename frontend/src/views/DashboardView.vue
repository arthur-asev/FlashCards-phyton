<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ArrowUpRight, CalendarDays, RefreshCw } from "@lucide/vue";

import { api } from "../services/api";
import type { Flashcard, ReviewStats } from "../types";

const emit = defineEmits<{ navigate: [view: "import" | "library" | "review"] }>();
const stats = ref<ReviewStats | null>(null);
const dueCards = ref<Flashcard[]>([]);
const loading = ref(true);
const errorMessage = ref("");

async function loadDashboard() {
  loading.value = true;
  errorMessage.value = "";
  try {
    const [reviewStats, due] = await Promise.all([api.getReviewStats(), api.getDueCards(4)]);
    stats.value = reviewStats;
    dueCards.value = due.items;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Falha ao carregar o resumo.";
  } finally {
    loading.value = false;
  }
}

onMounted(loadDashboard);
</script>

<template>
  <section class="view-stack">
    <header class="page-heading">
      <div>
        <p class="eyebrow">VISÃO GERAL</p>
        <h1>Seu espaço de estudo</h1>
        <p class="heading-note">Acompanhe seus decks e retome a revisão.</p>
      </div>
      <button class="button button-quiet" type="button" :disabled="loading" @click="loadDashboard">
        <RefreshCw :size="16" :class="{ spinning: loading }" aria-hidden="true" />
        Atualizar
      </button>
    </header>

    <p v-if="errorMessage" class="notice notice-error" role="alert">{{ errorMessage }}</p>

    <div class="metric-grid">
      <article class="metric-panel metric-primary">
        <span class="metric-label">Para revisar agora</span>
        <strong>{{ loading ? "—" : stats?.due_cards ?? 0 }}</strong>
        <button class="text-action" type="button" @click="emit('navigate', 'review')">
          Abrir fila <ArrowUpRight :size="15" aria-hidden="true" />
        </button>
        <CalendarDays class="metric-watermark" :size="46" :stroke-width="1.4" aria-hidden="true" />
      </article>
      <article class="metric-panel">
        <span class="metric-label">Cards no acervo</span>
        <strong>{{ loading ? "—" : stats?.total_cards ?? 0 }}</strong>
        <button class="text-action" type="button" @click="emit('navigate', 'library')">
          Ver biblioteca <ArrowUpRight :size="15" aria-hidden="true" />
        </button>
      </article>
      <article class="metric-panel">
        <span class="metric-label">Já revisados</span>
        <strong>{{ loading ? "—" : stats?.reviewed_cards ?? 0 }}</strong>
        <span class="metric-foot">{{ stats?.total_reviews ?? 0 }} sessões registradas</span>
      </article>
      <article class="metric-panel metric-accent">
        <span class="metric-label">Ainda sem revisão</span>
        <strong>{{ loading ? "—" : stats?.pending_cards ?? 0 }}</strong>
        <button class="text-action" type="button" @click="emit('navigate', 'import')">
          Importar planilha <ArrowUpRight :size="15" aria-hidden="true" />
        </button>
      </article>
    </div>

    <section class="content-section">
      <div class="section-heading">
        <div>
          <p class="eyebrow">REVISÃO</p>
          <h2>Próximos cards</h2>
        </div>
        <button class="button button-outline" type="button" @click="emit('navigate', 'review')">
          Abrir revisão <ArrowUpRight :size="16" aria-hidden="true" />
        </button>
      </div>

      <div v-if="loading" class="loading-line">Carregando cards…</div>
      <div v-else-if="dueCards.length" class="due-list">
        <article v-for="(card, index) in dueCards" :key="card.id" class="due-row">
          <span class="row-index">{{ String(index + 1).padStart(2, "0") }}</span>
          <div class="due-copy">
            <strong>{{ card.front }}</strong>
            <span>{{ card.back }}</span>
          </div>
          <span class="due-tag">{{ card.difficulty || "Geral" }}</span>
        </article>
      </div>
      <div v-else class="empty-state">
        <CalendarDays :size="22" aria-hidden="true" />
        <div>
          <strong>Fila em dia</strong>
          <p>Não há cards pendentes neste momento.</p>
        </div>
      </div>
    </section>

    <section class="quick-actions" aria-label="Ações">
      <button type="button" class="quick-action" @click="emit('navigate', 'import')">
        <span class="quick-number">01</span>
        <span><strong>Adicionar conteúdo</strong><small>Enviar CSV, XLS ou XLSX</small></span>
        <ArrowUpRight :size="18" aria-hidden="true" />
      </button>
      <button type="button" class="quick-action" @click="emit('navigate', 'library')">
        <span class="quick-number">02</span>
        <span><strong>Organizar biblioteca</strong><small>Decks, cards e tags</small></span>
        <ArrowUpRight :size="18" aria-hidden="true" />
      </button>
    </section>
  </section>
</template>

<style scoped>
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-panel {
  position: relative;
  display: flex;
  min-height: 156px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  overflow: hidden;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.metric-panel strong {
  font-family: var(--font-display);
  font-size: 38px;
  font-weight: 600;
  line-height: 1;
}

.metric-label,
.metric-foot {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.metric-foot {
  font-weight: 400;
}

.metric-primary {
  border-color: var(--ink);
  background: var(--ink);
  color: #fff;
}

.metric-primary .metric-label,
.metric-primary .text-action {
  color: #c8d9d4;
}

.metric-primary .text-action:hover {
  color: #fff;
}

.metric-primary .metric-watermark {
  position: absolute;
  right: 16px;
  top: 16px;
  color: #55766e;
}

.metric-accent {
  border-top: 3px solid var(--coral);
}

.text-action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--teal);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.section-heading h2 {
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-size: 23px;
  font-weight: 600;
}

.due-list {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.due-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  min-height: 70px;
  padding: 12px 18px;
  border-bottom: 1px solid var(--line-soft);
}

.due-row:last-child {
  border-bottom: 0;
}

.row-index,
.quick-number {
  color: var(--coral);
  font-family: var(--font-mono);
  font-size: 12px;
}

.due-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.due-copy strong,
.due-copy span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.due-copy strong {
  font-size: 13px;
  font-weight: 650;
}

.due-copy span {
  color: var(--muted);
  font-size: 12px;
}

.due-tag {
  border-radius: 4px;
  background: var(--surface-tint);
  color: var(--muted);
  padding: 5px 8px;
  font-size: 11px;
}

.empty-state {
  display: flex;
  align-items: center;
  gap: 13px;
  min-height: 102px;
  padding: 20px;
  border: 1px dashed var(--line-strong);
  border-radius: 8px;
  color: var(--teal);
}

.empty-state strong {
  color: var(--ink);
}

.empty-state p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.loading-line {
  padding: 26px 0;
  color: var(--muted);
  font-size: 13px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.quick-action {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 13px;
  min-height: 78px;
  padding: 14px 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  transition: border-color 160ms ease, transform 160ms ease;
}

.quick-action:hover {
  transform: translateY(-2px);
  border-color: var(--teal);
}

.quick-action > span:nth-child(2) {
  display: grid;
  gap: 4px;
}

.quick-action strong {
  font-size: 13px;
}

.quick-action small {
  color: var(--muted);
  font-size: 11px;
}

@media (max-width: 980px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .metric-panel {
    min-height: 140px;
    padding: 14px;
  }

  .metric-panel strong {
    font-size: 32px;
  }

  .due-row {
    grid-template-columns: 28px minmax(0, 1fr);
    padding: 12px;
  }

  .due-tag {
    display: none;
  }

  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>