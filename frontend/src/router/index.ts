import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import MapPage from '../pages/MapPage.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'map',
        component: MapPage
      },
      // Nueva ruta para la página de reportes
      {
        path: 'reports',
        name: 'reports',
        // Usamos import dinámico para lazy loading
        component: () => import('../modules/reports/pages/ReportPage.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router