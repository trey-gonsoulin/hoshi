import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChartStoreContext, useChartStoreProvider } from '@/hooks/useChartStore'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

function Root() {
  const store = useChartStoreProvider()
  return (
    <ChartStoreContext.Provider value={store}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ChartStoreContext.Provider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Root />
    </QueryClientProvider>
  </StrictMode>,
)
