import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'

type Theme = 'light' | 'dark'
type ThemeMode = Theme | 'system'

type ThemeProviderProps = PropsWithChildren<{
  defaultTheme?: ThemeMode
  storageKey?: string
}>

type ThemeContextValue = {
  theme: ThemeMode
  resolvedTheme: Theme
  setTheme: (value: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const MEDIA_QUERY = '(prefers-color-scheme: dark)'
const DEFAULT_STORAGE_KEY = 'proximeter-theme'

function getSystemTheme(): Theme {
  if (typeof window === 'undefined') {
    return 'light'
  }

  return window.matchMedia(MEDIA_QUERY).matches ? 'dark' : 'light'
}

function getInitialTheme(storageKey: string, defaultTheme: ThemeMode): ThemeMode {
  if (typeof window === 'undefined') {
    return defaultTheme
  }

  const storedTheme = window.localStorage.getItem(storageKey)
  if (storedTheme === 'light' || storedTheme === 'dark' || storedTheme === 'system') {
    return storedTheme
  }

  return defaultTheme
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = DEFAULT_STORAGE_KEY,
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<ThemeMode>(() => getInitialTheme(storageKey, defaultTheme))
  const [systemTheme, setSystemTheme] = useState<Theme>(() => getSystemTheme())

  const resolvedTheme = theme === 'system' ? systemTheme : theme

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    if (theme === 'system') {
      const media = window.matchMedia(MEDIA_QUERY)
      const applySystemTheme = () => setSystemTheme(media.matches ? 'dark' : 'light')

      applySystemTheme()
      media.addEventListener('change', applySystemTheme)
      return () => media.removeEventListener('change', applySystemTheme)
    }

    setSystemTheme(getSystemTheme())
  }, [theme])

  useEffect(() => {
    if (typeof document === 'undefined') {
      return
    }

    const root = document.documentElement
    root.dataset['theme'] = resolvedTheme
    root.classList.toggle('dark', resolvedTheme === 'dark')
  }, [resolvedTheme])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    window.localStorage.setItem(storageKey, theme)
  }, [storageKey, theme])

  const setTheme = useCallback((value: ThemeMode) => {
    setThemeState(value)
  }, [])

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme }),
    [resolvedTheme, setTheme, theme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)

  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }

  return context
}
