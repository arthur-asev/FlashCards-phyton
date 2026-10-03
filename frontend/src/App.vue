<script setup lang="ts">
import { computed, ref, type Component } from "vue";
import {
  BookOpenCheck,
  CalendarDays,
  FileSpreadsheet,
  LayoutDashboard,
  Library,
  Plus,
  Sparkles,
} from "@lucide/vue";

import DashboardView from "./views/DashboardView.vue";
import GenerateView from "./views/GenerateView.vue";
import ImportView from "./views/ImportView.vue";
import LibraryView from "./views/LibraryView.vue";
import ReviewView from "./views/ReviewView.vue";

type ViewName = "dashboard" | "import" | "library" | "generate" | "review";
type NavItem = {
  id: ViewName;
  label: string;
  compactLabel: string;
  icon: Component;
  group: "ESTUDO" | "ACERVO";
};

const activeView = ref<ViewName>("dashboard");
const newCardRequest = ref(0);
const navItems: NavItem[] = [
  { id: "dashboard", label: "Visão geral", compactLabel: "Início", icon: LayoutDashboard, group: "ESTUDO" },
  { id: "review", label: "Revisão", compactLabel: "Revisão", icon: BookOpenCheck, group: "ESTUDO" },
  { id: "library", label: "Biblioteca", compactLabel: "Acervo", icon: Library, group: "ACERVO" },
  { id: "import", label: "Importar", compactLabel: "Importar", icon: FileSpreadsheet, group: "ACERVO" },
  { id: "generate", label: "Gerar com IA", compactLabel: "Gerar IA", icon: Sparkles, group: "ACERVO" },
];
const pageTitle = computed(() => navItems.find((item) => item.id === activeView.value)?.label ?? "Estudo");
const today = new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit", month: "long" }).format(new Date());

function navigate(view: ViewName) {
  activeView.value = view;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function createCard() {
  activeView.value = "library";
  newCardRequest.value += 1;
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <button class="brand-lockup" type="button" aria-label="Ir para visão geral" @click="navigate('dashboard')">
        <span class="brand-mark" aria-hidden="true"><i /><i /><i /></span>
        <span class="brand-type"><strong>FOLIO</strong><small>FLASHCARD STUDIO</small></span>
      </button>

      <nav class="primary-nav" aria-label="Navegação principal">
        <template v-for="group in ['ESTUDO', 'ACERVO'] as const" :key="group">
          <p class="nav-group-label">{{ group }}</p>
          <button
            v-for="item in navItems.filter((navItem) => navItem.group === group)"
            :key="item.id"
            type="button"
            class="nav-item"
            :class="{ active: activeView === item.id }"
            :aria-current="activeView === item.id ? 'page' : undefined"
            @click="navigate(item.id)"
          >
            <component :is="item.icon" :size="17" :stroke-width="1.8" aria-hidden="true" />
            <span class="nav-label-full">{{ item.label }}</span>
            <span class="nav-label-compact">{{ item.compactLabel }}</span>
            <span v-if="item.id === 'review'" class="nav-mark"><CalendarDays :size="13" /></span>
          </button>
        </template>
      </nav>

      <div class="sidebar-bottom">
        <div class="sidebar-rule" />
        <div class="sidebar-caption"><span class="status-light" /> PLATAFORMA DE ESTUDO</div>
        <div class="sidebar-version">FOLIO <span>·</span> 01</div>
      </div>
    </aside>

    <div class="main-column">
      <header class="topbar">
        <div class="topbar-crumb"><span>FOLIO</span><b>/</b><strong>{{ pageTitle }}</strong></div>
        <div class="topbar-right">
          <span class="today-label">{{ today }}</span>
          <button class="topbar-add" type="button" aria-label="Criar card" title="Criar card" @click="createCard">
            <Plus :size="17" aria-hidden="true" />
          </button>
        </div>
      </header>

      <main class="main-content">
        <Transition name="view" mode="out-in">
          <DashboardView v-if="activeView === 'dashboard'" key="dashboard" @navigate="navigate" />
          <ReviewView v-else-if="activeView === 'review'" key="review" />
          <LibraryView v-else-if="activeView === 'library'" key="library" :new-card-request="newCardRequest" />
          <ImportView v-else-if="activeView === 'import'" key="import" />
          <GenerateView v-else key="generate" />
        </Transition>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell { display: grid; min-height: 100vh; grid-template-columns: 238px minmax(0, 1fr); }
.sidebar { position: sticky; top: 0; display: flex; height: 100vh; flex-direction: column; padding: 23px 15px 17px; background: var(--ink); color: #e9f0ec; }
.brand-lockup { display: flex; align-items: center; gap: 11px; padding: 2px 9px 25px; border: 0; background: transparent; color: inherit; cursor: pointer; text-align: left; }
.brand-mark { position: relative; display: flex; width: 30px; height: 30px; align-items: flex-end; gap: 3px; padding: 5px; border: 1px solid rgba(229, 244, 237, 0.6); border-radius: 6px 6px 6px 2px; transform: rotate(-4deg); }
.brand-mark i { display: block; width: 4px; border-radius: 3px 3px 0 0; background: #8bd2b6; }
.brand-mark i:nth-child(1) { height: 8px; }
.brand-mark i:nth-child(2) { height: 13px; background: #e6a36e; }
.brand-mark i:nth-child(3) { height: 17px; }
.brand-type { display: grid; gap: 2px; }
.brand-type strong { font-family: var(--font-display); font-size: 15px; letter-spacing: 0.12em; }
.brand-type small { color: #9fb7ad; font-family: var(--font-mono); font-size: 8px; }
.primary-nav { display: grid; gap: 3px; }
.nav-group-label { margin: 14px 10px 6px; color: #89a197; font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.12em; }
.nav-item { display: flex; position: relative; width: 100%; min-height: 40px; align-items: center; gap: 11px; padding: 0 10px; border: 1px solid transparent; border-radius: 5px; background: transparent; color: #c8d7d0; cursor: pointer; font-size: 12px; text-align: left; transition: background 140ms ease, color 140ms ease; }
.nav-item:hover { background: rgba(255, 255, 255, 0.07); color: #fff; }
.nav-item.active { border-color: rgba(180, 220, 204, 0.15); background: #29453e; color: #f7fffb; }
.nav-item.active::before { position: absolute; left: 0; width: 3px; height: 22px; border-radius: 0 3px 3px 0; background: #79c8a8; content: ""; }
.nav-item span:nth-child(2) { flex: 1; }
.nav-label-compact { display: none; }
.nav-mark { display: grid; color: #93b5a7; }
.sidebar-bottom { margin-top: auto; padding: 0 9px; }
.sidebar-rule { height: 1px; margin-bottom: 14px; background: rgba(207, 227, 218, 0.14); }
.sidebar-caption { display: flex; align-items: center; gap: 7px; color: #9eb2aa; font-family: var(--font-mono); font-size: 8px; }
.status-light { width: 6px; height: 6px; border-radius: 50%; background: #7ac7a3; box-shadow: 0 0 0 3px rgba(122, 199, 163, 0.12); }
.sidebar-version { margin-top: 12px; color: #718b80; font-family: var(--font-mono); font-size: 9px; }
.sidebar-version span { padding: 0 4px; color: #c77a5d; }
.main-column { min-width: 0; }
.topbar { position: sticky; z-index: 5; top: 0; display: flex; height: 57px; align-items: center; justify-content: space-between; padding: 0 34px; border-bottom: 1px solid var(--line); background: rgba(249, 251, 248, 0.92); backdrop-filter: blur(12px); }
.topbar-crumb { display: flex; align-items: center; gap: 10px; color: var(--muted); font-family: var(--font-mono); font-size: 10px; }
.topbar-crumb b { color: #b5c3bc; font-weight: 400; }
.topbar-crumb strong { color: var(--ink); font-family: var(--font-sans); font-size: 12px; font-weight: 650; }
.topbar-right { display: flex; align-items: center; gap: 15px; }
.today-label { color: var(--muted); font-size: 11px; text-transform: capitalize; }
.topbar-add { display: grid; width: 31px; height: 31px; place-items: center; border: 1px solid var(--line); border-radius: 5px; background: var(--surface); color: var(--teal); cursor: pointer; }
.topbar-add:hover { border-color: var(--teal); background: #edf6f1; }
.main-content { width: min(1440px, 100%); margin: 0 auto; padding: 30px 34px 48px; }
.view-enter-active, .view-leave-active { transition: opacity 120ms ease, transform 120ms ease; }
.view-enter-from { opacity: 0; transform: translateY(5px); }
.view-leave-to { opacity: 0; transform: translateY(-3px); }
@media (max-width: 900px) {
  .app-shell { display: block; }
  .sidebar { position: sticky; z-index: 10; top: 0; width: 100%; height: auto; padding: 9px 14px 0; }
  .brand-lockup { padding: 1px 5px 8px; }
  .brand-mark { width: 26px; height: 26px; }
  .brand-type { display: flex; align-items: baseline; gap: 8px; }
  .brand-type strong { font-size: 13px; }
  .brand-type small { font-size: 7px; }
  .primary-nav { display: flex; overflow-x: auto; gap: 3px; padding-bottom: 8px; scrollbar-width: none; }
  .primary-nav::-webkit-scrollbar { display: none; }
  .nav-group-label { display: none; }
  .nav-item { width: auto; min-width: max-content; min-height: 35px; gap: 7px; padding: 0 10px; font-size: 11px; }
  .nav-item.active::before { top: auto; bottom: 0; left: 12px; width: calc(100% - 24px); height: 2px; }
  .nav-mark, .sidebar-bottom { display: none; }
  .topbar { top: 91px; height: 48px; padding: 0 22px; }
  .main-content { padding: 25px 22px 40px; }
}
@media (max-width: 560px) {
  .primary-nav { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); overflow: visible; gap: 2px; padding-bottom: 5px; }
  .nav-item { min-width: 0; min-height: 43px; flex-direction: column; justify-content: center; gap: 2px; padding: 3px 1px; font-size: 9px; }
  .nav-item svg { width: 15px; height: 15px; }
  .nav-label-full { display: none; }
  .nav-item .nav-label-compact { display: block; max-width: 100%; overflow: visible; white-space: nowrap; }
  .nav-item.active::before { left: 8px; width: calc(100% - 16px); }
  .topbar { top: 101px; padding: 0 15px; }
  .today-label { display: none; }
  .main-content { padding: 20px 14px 32px; }
}
</style>
