<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { AlertCircle, Check, ChevronDown, FileSpreadsheet, Upload } from "@lucide/vue";

import { api, ApiError } from "../services/api";
import type { Deck, ImportResult, SpreadsheetPreview, SpreadsheetValidation, UploadedFile } from "../types";

const targets = [
  { key: "front", label: "Frente", required: true },
  { key: "back", label: "Verso", required: true },
  { key: "explanation", label: "Explicação", required: false },
  { key: "subject", label: "Matéria", required: false },
  { key: "topic", label: "Assunto", required: false },
  { key: "tags", label: "Tags", required: false },
  { key: "difficulty", label: "Dificuldade", required: false },
  { key: "source", label: "Origem", required: false },
] as const;

const selectedFile = ref<File | null>(null);
const decks = ref<Deck[]>([]);
const selectedDeckId = ref("");
const uploadedFile = ref<UploadedFile | null>(null);
const preview = ref<SpreadsheetPreview | null>(null);
const mapping = ref<Record<string, string>>({});
const validation = ref<SpreadsheetValidation | null>(null);
const importResult = ref<ImportResult | null>(null);
const busy = ref(false);
const errorMessage = ref("");
const fileInput = ref<HTMLInputElement | null>(null);
const mappedCount = computed(() => Object.values(mapping.value).filter(Boolean).length);
const activeMapping = computed(() =>
  Object.fromEntries(Object.entries(mapping.value).filter(([, column]) => Boolean(column))),
);

watch(
  mapping,
  () => {
    validation.value = null;
    importResult.value = null;
  },
  { deep: true },
);

const emit = defineEmits<{ navigate: [view: "library"] }>();

async function loadDecks() {
  try {
    const page = await api.listDecks();
    decks.value = page.items;
    selectedDeckId.value = decks.value[0]?.id ?? "";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível carregar os decks.";
  }
}

onMounted(loadDecks);

function suggestMapping(columns: string[]) {
  const normalized = columns.map((column) => column.trim().toLocaleLowerCase());
  const synonyms: Record<string, string[]> = {
    front: ["front", "frente", "pergunta", "question"],
    back: ["back", "verso", "resposta", "answer"],
    explanation: ["explanation", "explicação", "explicacao", "comentário", "comentario"],
    subject: ["subject", "matéria", "materia", "disciplina"],
    topic: ["topic", "assunto", "tema"],
    tags: ["tags", "tag", "etiquetas"],
    difficulty: ["difficulty", "dificuldade"],
    source: ["source", "origem", "fonte"],
  };
  const next: Record<string, string> = {};
  for (const target of targets) {
    const index = normalized.findIndex((column) => synonyms[target.key].includes(column));
    next[target.key] = index >= 0 ? columns[index] : "";
  }
  mapping.value = next;
}

async function loadPreview(sheetName?: string) {
  if (!uploadedFile.value) return;
  preview.value = await api.previewFile(uploadedFile.value.id, sheetName);
  if (!sheetName) suggestMapping(preview.value.preview.columns);
  validation.value = null;
  importResult.value = null;
}

async function uploadSelectedFile() {
  if (!selectedFile.value) return;
  busy.value = true;
  errorMessage.value = "";
  validation.value = null;
  try {
    uploadedFile.value = await api.uploadFile(selectedFile.value);
    await loadPreview();
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Não foi possível enviar o arquivo.";
  } finally {
    busy.value = false;
  }
}

async function changeSheet(event: Event) {
  const sheetName = (event.target as HTMLSelectElement).value;
  busy.value = true;
  errorMessage.value = "";
  try {
    await loadPreview(sheetName);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível abrir a aba.";
  } finally {
    busy.value = false;
  }
}

async function validateMapping() {
  if (!uploadedFile.value || !preview.value) return;
  busy.value = true;
  errorMessage.value = "";
  try {
    validation.value = await api.validateFile(
      uploadedFile.value.id,
      preview.value.preview.selected_sheet,
      activeMapping.value,
    );
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Não foi possível validar o mapeamento.";
  } finally {
    busy.value = false;
  }
}

async function importCards() {
  if (!uploadedFile.value || !preview.value || !validation.value?.valid || !selectedDeckId.value) return;
  busy.value = true;
  errorMessage.value = "";
  try {
    importResult.value = await api.importFile({
      file_id: uploadedFile.value.id,
      deck_id: selectedDeckId.value,
      sheet_name: preview.value.preview.selected_sheet,
      mapping: activeMapping.value,
    });
  } catch (error) {
    errorMessage.value = error instanceof ApiError ? error.message : "Não foi possível importar os cards.";
  } finally {
    busy.value = false;
  }
}

function resetImport() {
  selectedFile.value = null;
  uploadedFile.value = null;
  preview.value = null;
  validation.value = null;
  importResult.value = null;
  mapping.value = {};
  errorMessage.value = "";
  if (fileInput.value) fileInput.value.value = "";
}

function formatBytes(value: number): string {
  return value < 1024 * 1024 ? `${Math.max(1, Math.round(value / 1024))} KB` : `${(value / 1024 / 1024).toFixed(1)} MB`;
}
</script>

<template>
  <section class="view-stack">
    <header class="page-heading">
      <div>
        <p class="eyebrow">ENTRADA DE DADOS</p>
        <h1>Importar planilha</h1>
        <p class="heading-note">CSV, XLS e XLSX <span class="dot-separator">/</span> até 25 MB</p>
      </div>
      <button v-if="uploadedFile" class="button button-quiet" type="button" @click="resetImport">
        Novo arquivo
      </button>
    </header>

    <p v-if="errorMessage" class="notice notice-error" role="alert">
      <AlertCircle :size="16" aria-hidden="true" /> {{ errorMessage }}
    </p>

    <section v-if="!uploadedFile" class="upload-stage">
      <input
        ref="fileInput"
        class="visually-hidden"
        type="file"
        accept=".csv,.xls,.xlsx"
        @change="selectedFile = ($event.target as HTMLInputElement).files?.[0] ?? null"
      />
      <div class="upload-mark"><FileSpreadsheet :size="25" aria-hidden="true" /></div>
      <h2>{{ selectedFile?.name ?? "Selecione um arquivo" }}</h2>
      <p v-if="selectedFile" class="upload-meta">{{ formatBytes(selectedFile.size) }}</p>
      <button v-else class="button button-outline" type="button" @click="fileInput?.click()">
        <Upload :size="16" aria-hidden="true" /> Escolher arquivo
      </button>
      <button
        v-if="selectedFile"
        class="button button-primary"
        type="button"
        :disabled="busy"
        @click="uploadSelectedFile"
      >
        <Upload :size="16" aria-hidden="true" /> {{ busy ? "Enviando…" : "Enviar arquivo" }}
      </button>
      <button v-if="selectedFile" class="text-link" type="button" @click="fileInput?.click()">
        Trocar arquivo
      </button>
    </section>

    <template v-else-if="preview">
      <section class="file-summary">
        <div class="file-leading"><FileSpreadsheet :size="19" aria-hidden="true" /></div>
        <div class="file-summary-copy">
          <strong>{{ uploadedFile?.filename }}</strong>
          <span>{{ preview.preview.format.toUpperCase() }} · {{ formatBytes(preview.size) }} · {{ preview.preview.row_count }} linhas</span>
        </div>
        <span class="checksum-chip">SHA-256 {{ preview.checksum.slice(0, 10) }}</span>
      </section>

      <section class="content-section">
        <div class="section-heading">
          <div>
            <p class="eyebrow">PRÉVIA</p>
            <h2>{{ preview.preview.selected_sheet }}</h2>
          </div>
          <label v-if="preview.preview.sheet_names.length > 1" class="select-with-icon">
            <span class="visually-hidden">Selecionar aba</span>
            <select :value="preview.preview.selected_sheet" :disabled="busy" @change="changeSheet">
              <option v-for="sheet in preview.preview.sheet_names" :key="sheet" :value="sheet">{{ sheet }}</option>
            </select>
            <ChevronDown :size="15" aria-hidden="true" />
          </label>
          <span v-else class="quiet-count">{{ preview.preview.columns.length }} colunas</span>
        </div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th v-for="column in preview.preview.columns" :key="column">{{ column }}</th></tr></thead>
            <tbody>
              <tr v-for="(row, rowIndex) in preview.preview.rows" :key="rowIndex">
                <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell || "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="table-footer">Exibindo {{ preview.preview.rows.length }} de {{ preview.preview.row_count }} linhas</div>
      </section>

      <section class="content-section mapping-section">
        <div class="section-heading">
          <div>
            <p class="eyebrow">MAPEAMENTO</p>
            <h2>Associe as colunas</h2>
          </div>
          <span class="quiet-count">{{ mappedCount }} campos</span>
        </div>
        <div class="mapping-grid">
          <label v-for="target in targets" :key="target.key" class="mapping-field">
            <span>{{ target.label }} <b v-if="target.required">*</b></span>
            <select v-model="mapping[target.key]">
              <option value="">Não mapear</option>
              <option v-for="column in preview.preview.columns" :key="column" :value="column">{{ column }}</option>
            </select>
          </label>
        </div>
        <div class="mapping-footer">
          <span class="quiet-count">Frente e verso são obrigatórios.</span>
          <div class="mapping-actions">
            <button class="button button-outline" type="button" :disabled="busy" @click="validateMapping">
              <Check :size="16" aria-hidden="true" /> {{ busy ? "Validando…" : "Validar" }}
            </button>
          </div>
        </div>
      </section>

      <section v-if="validation?.valid" class="import-confirmation">
        <label class="form-field">Adicionar cards ao deck
          <select v-model="selectedDeckId" :disabled="busy || Boolean(importResult)">
            <option value="">Selecione um deck</option>
            <option v-for="deck in decks" :key="deck.id" :value="deck.id">{{ deck.name }}</option>
          </select>
        </label>
        <button v-if="decks.length" class="button button-primary" type="button" :disabled="busy || !selectedDeckId || Boolean(importResult)" @click="importCards">
          <Check :size="16" aria-hidden="true" /> {{ busy ? "Importando…" : `Importar ${validation.valid_rows} cards` }}
        </button>
        <button v-else class="button button-outline" type="button" @click="emit('navigate', 'library')">Criar deck primeiro</button>
        <p v-if="importResult" class="notice notice-success" role="status">
          <Check :size="16" aria-hidden="true" /> {{ importResult.processed_rows }} cards importados com sucesso.
        </p>
      </section>

      <section v-if="validation" class="validation-panel" :class="validation.valid ? 'validation-ok' : 'validation-warn'" aria-live="polite">
        <div class="validation-title">
          <Check v-if="validation.valid" :size="18" aria-hidden="true" />
          <AlertCircle v-else :size="18" aria-hidden="true" />
          <strong>{{ validation.valid ? "Planilha válida" : "Ajustes necessários" }}</strong>
          <span>{{ validation.valid_rows }} de {{ validation.checked_rows }} linhas válidas</span>
        </div>
        <ul v-if="validation.issues.length" class="issue-list">
          <li v-for="(issue, index) in validation.issues.slice(0, 8)" :key="`${issue.code}-${index}`">
            <span>{{ issue.row ? `Linha ${issue.row}` : "Mapeamento" }}</span>{{ issue.message }}
          </li>
          <li v-if="validation.issues.length > 8" class="more-issues">+ {{ validation.issues.length - 8 }} ocorrências</li>
        </ul>
        <div v-if="validation.valid" class="normalized-preview">
          <p class="eyebrow">PRIMEIROS REGISTROS</p>
          <div v-for="(row, index) in validation.normalized_rows.slice(0, 3)" :key="index" class="normalized-row">
            <strong>{{ row.front }}</strong><span>{{ row.back }}</span>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.upload-stage {
  display: flex;
  min-height: 300px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 13px;
  border: 1px dashed #b9c9c1;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.7);
  text-align: center;
}

.upload-mark,
.file-leading {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 8px;
  background: #e2efea;
  color: var(--teal);
}

.upload-stage h2 {
  max-width: min(90%, 560px);
  overflow: hidden;
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-meta,
.heading-note {
  color: var(--muted);
  font-size: 12px;
}

.text-link {
  border: 0;
  background: transparent;
  color: var(--teal);
  cursor: pointer;
  font-size: 12px;
  font-weight: 650;
}

.file-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.file-leading {
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
}

.file-summary-copy {
  display: grid;
  min-width: 0;
  gap: 4px;
}

.file-summary-copy strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-summary-copy span,
.checksum-chip,
.quiet-count {
  color: var(--muted);
  font-size: 11px;
}

.checksum-chip {
  margin-left: auto;
  padding: 5px 8px;
  border-radius: 4px;
  background: var(--surface-tint);
  font-family: var(--font-mono);
  white-space: nowrap;
}

.table-scroll {
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px 8px 0 0;
  background: var(--surface);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.data-table th,
.data-table td {
  max-width: 320px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--line-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-table th {
  position: sticky;
  top: 0;
  background: #edf3ef;
  color: #4b635a;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
}

.data-table td {
  color: var(--ink-soft);
  font-size: 12px;
}

.table-footer {
  padding: 8px 13px;
  border: 1px solid var(--line);
  border-top: 0;
  border-radius: 0 0 8px 8px;
  background: #fafcf9;
  color: var(--muted);
  font-size: 10px;
}

.select-with-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.select-with-icon svg {
  position: absolute;
  right: 10px;
  pointer-events: none;
}

.select-with-icon select {
  appearance: none;
  padding-right: 34px;
}

.mapping-section {
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.mapping-section .section-heading {
  margin-bottom: 17px;
}

.mapping-section h2 {
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 600;
}

.mapping-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.mapping-field {
  display: grid;
  gap: 6px;
  color: var(--ink-soft);
  font-size: 11px;
  font-weight: 650;
}

.mapping-field b {
  color: var(--coral);
}

.mapping-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 18px;
  padding-top: 15px;
  border-top: 1px solid var(--line-soft);
}

.validation-panel {
  padding: 16px 18px;
  border: 1px solid;
  border-radius: 8px;
}

.validation-ok {
  border-color: #b6d9ca;
  background: #edf7f2;
  color: #236649;
}

.validation-warn {
  border-color: #ead0a4;
  background: #fff8eb;
  color: #8a5b13;
}

.validation-title {
  display: flex;
  align-items: center;
  gap: 9px;
}

.validation-title span {
  margin-left: auto;
  font-size: 11px;
}

.issue-list {
  display: grid;
  gap: 7px;
  margin: 13px 0 0;
  padding: 12px 0 0;
  border-top: 1px solid currentColor;
  list-style: none;
}

.issue-list li {
  display: flex;
  gap: 10px;
  font-size: 12px;
}

.issue-list li span {
  flex: 0 0 86px;
  font-family: var(--font-mono);
  font-size: 10px;
}

.more-issues {
  font-weight: 700;
}

.normalized-preview {
  margin-top: 16px;
  padding-top: 13px;
  border-top: 1px solid #b6d9ca;
}

.normalized-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  padding: 9px 0;
  border-bottom: 1px solid #d8e9e1;
  color: var(--ink);
  font-size: 12px;
}

.normalized-row:last-child {
  border-bottom: 0;
}

.normalized-row span {
  color: var(--muted);
}

.notice-error {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 850px) {
  .mapping-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .upload-stage {
    min-height: 250px;
    padding: 18px;
  }

  .checksum-chip {
    display: none;
  }

  .mapping-grid {
    grid-template-columns: 1fr 1fr;
  }

  .mapping-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .mapping-footer .button {
    width: 100%;
  }
}
</style>
