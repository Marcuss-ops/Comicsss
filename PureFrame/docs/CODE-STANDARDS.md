# PureFrame TypeScript Coding Standards

> Le regole fondamentali per scrivere codice TypeScript pulito, scalabile e professionale in PureFrame.

---

## 🎯 Filosofia

**TypeScript NON serve a tipizzare tutto.**

Serve a rendere il codice:
- **Prevedibile** — comportamento chiaro e deducibile
- **Sicuro** — errori catturati a compile time
- **Facile da cambiare** — refactoring senza paura

Se stai scrivendo un tipo super complicato, fermati. Probabilmente stai andando nella direzione sbagliata.

---

## 💪 Hardware Minimo, Risultato Massimo

**PureFrame funziona su una VPS da $22.99/anno.** Questo non è un compromesso, è un obiettivo.

### Regole per l'Efficienza

| Regola | Motivo |
|--------|--------|
| **No allocazioni inutili** | Ogni `new` nel hot path è un costo |
| **No copie profonde** | Usa reference quando possibile |
| **No regex nel render** | Pre-compila o usa string operations |
| **No JSON.parse nel frame** | Parsea una volta, usa sempre |
| **No fs.readFileSync nel render** | Tutto in memoria prima |
| **No Promise.all per frame** | Sincrono = prevedibile |

### Benchmark Target

```
Hardware: 512 MB RAM, 1 vCore
Scene: 1080p30, 10 secondi, 3 layer
Obiettivo: < 60 secondi per render
Peak RAM: < 200 MB
```

Se il tuo codice non passa questi test, non è pronto.

---

## 📋 Le 5 Regole Fondamentali

### 1. Lascia lavorare l'Inference

**La differenza tra principiante e pro.** Scrivi meno tipi possibile e lascia che TypeScript capisca da solo.

#### ✅ Fai così

```typescript
const user = {
  id: 1,
  name: "Luca"
}; // TS capisce { id: number; name: string }

const items = [1, 2, 3]; // TS capisce number[]

function getName(user: User) {
  return user.name; // Return type inferred as string
}
```

#### ❌ Evita

```typescript
const user: { id: number; name: string } = {
  id: 1,
  name: "Luca"
}; // Ridondante

const items: number[] = [1, 2, 3]; // Ridondante

function getName(user: User): string {
  return user.name; // Return type ovvio
}
```

#### 📌 Quando scrivere tipi esplicitamente

| Scenario | Esempio | Motivo |
|----------|---------|--------|
| Input di funzioni pubbliche | `function process(data: InputType)` | Documentazione |
| Return type complessi | `function query(): Promise<Result[]>` | Chiarezza |
| Riuso di tipi | `type Status = "idle" \| "loading" \| "done"` | Riuso |
| Array vuoti | `const items: Item[] = []` | Correttezza |
| Override di inference | `const el = document.getElementById("x") as HTMLElement` | Necessità |

---

### 2. Usa `unknown`, non `any`

**`any` spegne TypeScript. `unknown` ti obbliga a controllare.**

#### ✅ Fai così

```typescript
function parseApiResponse(data: unknown) {
  if (typeof data === "string") {
    return data.toUpperCase();
  }
  
  if (typeof data === "object" && data !== null) {
    return JSON.stringify(data);
  }
  
  return String(data);
}
```

#### ❌ Evita

```typescript
function parseApiResponse(data: any) {
  return data.toUpperCase(); // 💥 Rischio crash se data non è string
}
```

#### 🔧 Helper type-safe per browser APIs

```typescript
// ✅ Invece di (window as any).webkitAudioContext()
function getAudioContext(): AudioContext {
  const AudioCtx = window.AudioContext 
    ?? (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  
  if (!AudioCtx) {
    throw new Error("AudioContext not supported");
  }
  
  return new AudioCtx();
}
```

#### 📌 Guida rapida

| Situazione | Usa |
|------------|-----|
| Input sconosciuto (API, user input) | `unknown` + type guards |
| Interop con librerie JS non tippate | `unknown` + cast controllato |
| Prototipo temporaneo (da tipizzare dopo) | `unknown` (mai `any`) |
| Browser API legacy | Helper type-safe |

---

### 3. Modella stati con Discriminated Unions

**Il pattern più potente in assoluto, soprattutto in React.**

#### ✅ Fai così

```typescript
// Definisci gli stati come union discriminata
type RequestState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: string };

// TypeScript sa esattamente cosa è disponibile in ogni stato
function UserCard({ state }: { state: RequestState<User> }) {
  switch (state.status) {
    case "idle":
      return <div>Pronto per caricare</div>;
    
    case "loading":
      return <Spinner />;
    
    case "success":
      // ✅ TypeScript sa che state.data esiste qui
      return <div>{state.data.name}</div>;
    
    case "error":
      // ✅ TypeScript sa che state.error esiste qui
      return <div>Errore: {state.error}</div>;
  }
}
```

#### ❌ Evita

```typescript
// ❌ Flag booleani confusi
interface UserState {
  isLoading: boolean;
  isSuccess: boolean;
  isError: boolean;
  data?: User;
  error?: string;
}

// ❌ Cosa succede se isLoading E isSuccess sono entrambi true?
// ❌ data è undefined? error è definito? Chi lo sa?
```

#### 📌 Pattern comuni in PureFrame

```typescript
// Zod schemas come discriminators
export const FillDeclarationSchema = z.union([
  z.object({ type: z.literal("solid"), color: z.string() }),
  z.object({ type: z.literal("linear-gradient"), stops: z.array(GradientStopSchema) }),
  z.object({ type: z.literal("radial-gradient"), stops: z.array(GradientStopSchema) }),
]);

// Flow states
type EditorState =
  | { mode: "preview" }
  | { mode: "edit"; selectedLayerId: string | null }
  | { mode: "export"; progress: number };
```

---

### 4. Usa Generics (senza esagerare)

**Potenti quando collegano input → output. Inutili se non aggiungono valore.**

#### ✅ Fai così

```typescript
// ✅ Generic collega input → output
function identity<T>(value: T): T {
  return value;
}

// ✅ Generic con constraint utile
function sortBy<T>(items: T[], key: keyof T): T[] {
  return [...items].sort((a, b) => 
    a[key] < b[key] ? -1 : a[key] > b[key] ? 1 : 0
  );
}

// ✅ Generic per factory functions
function createApiClient<T>(baseUrl: string): ApiClient<T> {
  return new ApiClient<T>(baseUrl);
}
```

#### ❌ Evita

```typescript
// ❌ Overengineering — `extends unknown` non aggiunge nulla
function identity<T extends unknown>(value: T): T { ... }

// ❌ Generic inutile — non collega input a output
function logValue<T>(value: T): void {
  console.log(value); // T non serve, bastava `unknown`
}

// ❌ Troppi generics
function transform<A, B, C, D>(a: A, b: B, c: C): D { ... }
// Difficile da capire e usare
```

#### 📌 Regola d'oro

| Chiediti | Risposta |
|----------|----------|
| Il generic collega input → output? | ✅ Usalo |
| Il generic permette riuso type-safe? | ✅ Usalo |
| Il generic aggiunge complessità senza valore? | ❌ Rimuovilo |
| Potresti usare `unknown` o un tipo fisso? | ❌ Non serve generic |

---

### 5. Configura TypeScript in Strict Mode

**Non negoziabile.** Strict mode trasforma TypeScript da "suggeritore" a "guardiano".

#### 📁 tsconfig.json

```json
{
  "compilerOptions": {
    "strict": true,
    
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true
  }
}
```

#### 📌 Cosa fa ogni opzione

| Opzione | Effetto |
|---------|---------|
| `strict` | Abilita tutte le verifiche strict |
| `noUncheckedIndexedAccess` | `arr[0]` restituisce `T \| undefined` |
| `exactOptionalPropertyTypes` | Distingue `undefined` da proprietà opzionale |
| `noFallthroughCasesInSwitch` | Errore se dimentichi `break` in switch |
| `noUnusedLocals` | Errore per variabili non usate |
| `noUnusedParameters` | Errore per parametri non usati |

---

## 🏗️ Pattern Specifici PureFrame

### Node Definitions

```typescript
// ✅ Struttura standard per un node
export function MyVisual(props: MyVisualProps): VisualNode {
  const resolved = resolveProps(props);
  
  return {
    type: "my-visual",
    render: (ctx, frame) => {
      // Pure rendering logic
    },
    duration: resolved.duration ?? DEFAULT_DURATION,
  };
}
```

### Zod Schemas

```typescript
// ✅ Schema con discriminated union
export const MySchema = z.object({
  type: z.literal("my-type"),
  variant: z.enum(["a", "b", "c"]),
  config: z.object({
    color: z.string().optional(),
    size: z.number().positive(),
  }),
});

export type MyType = z.infer<typeof MySchema>;
```

### Font System

```typescript
// ✅ Font source types — discriminated union
type FontSource =
  | { type: "local"; path: string }
  | { type: "google"; family: string; weight: number; style: "normal" | "italic"; subsets?: string[] }
  | { type: "url"; url: string };

// ✅ Font descriptor — what users declare in scenes
interface FontDescriptor {
  id: string;              // "inter-700"
  family: string;          // "Inter"
  weight: number;          // 400, 700
  style: "normal" | "italic";
  source: FontSource;
  features?: string[];     // OpenType features
  fallback?: string[];     // ["Noto Sans", "Arial"]
}

// ✅ Resolved font — after preload, stable for render
interface ResolvedFont {
  id: string;
  family: string;
  weight: number;
  style: "normal" | "italic";
  localPath: string;       // file reale già disponibile
  hash: string;            // per cache deterministica
  metrics: {
    ascent: number;
    descent: number;
    lineGap: number;
    unitsPerEm: number;
    capHeight?: number;
    xHeight?: number;
  };
}
```

#### Font Pipeline — Due Fasi

```typescript
// ✅ Fase 1: Resolve (prima del render)
// - Trova il file font
// - Scarica se necessario (Google/URL)
// - Salva in cache
// - Leggi metadati
// - Registra nel registry

// ✅ Fase 2: Render (durante i frame)
// - Lookup locale nel registry
// - Usa metriche già cacheate
// - Disegna il testo
// - MAI fetch nel frame renderer
```

#### Font Registry Pattern

```typescript
// ✅ Registry type-safe
class FontRegistry {
  private fonts = new Map<string, ResolvedFont>();

  register(font: ResolvedFont): void {
    this.fonts.set(font.id, font);
  }

  get(id: string): ResolvedFont {
    const font = this.fonts.get(id);
    if (!font) {
      throw new Error(`Font not found: ${id}. Did you forget to resolve it?`);
    }
    return font;
  }

  has(id: string): boolean {
    return this.fonts.has(id);
  }
}
```

#### Font Cache Strategy

```typescript
// ✅ Cache key deterministica
function createFontCacheKey(font: FontDescriptor): string {
  return hash({
    family: font.family,
    weight: font.weight,
    style: font.style,
    source: font.source,
  });
}

// ✅ Tre livelli di cache
// 1. File cache — font scaricato/copiato localmente
// 2. Metadata cache — metriche e info parseate
// 3. Text measurement cache — evita rimisurare
```

#### ❌ Anti-pattern Font

```typescript
// ❌ Fetch nel frame renderer
function renderFrame(ctx, frame) {
  const font = await fetchFont("Inter"); // NO!
  ctx.font = font;
}

// ❌ Misura testo prima che il font sia pronto
const metrics = measureText("Hello", "inter-700"); // Font non ancora registrato!

// ❌ Path sparsi ovunque
ctx.font = "bold 48px ./assets/fonts/Inter-Bold.ttf"; // Non deterministico
```

### Audio Nodes

### Error Handling

```typescript
// ✅ Discriminated union per risultati
type Result<T> =
  | { ok: true; value: T }
  | { ok: false; error: string };

function parseConfig(input: unknown): Result<Config> {
  const parsed = ConfigSchema.safeParse(input);
  
  if (!parsed.success) {
    return { ok: false, error: parsed.error.message };
  }
  
  return { ok: true, value: parsed.data };
}
```

---

## ❌ Cosa NON Fare

### Anti-pattern da evitare

```typescript
// ❌ any ovunque
function process(data: any): any { ... }

// ❌ Type assertions senza controllo
const el = document.getElementById("x")! as HTMLElement;

// ❌ Flag booleani per stati complessi
interface State {
  isLoading: boolean;
  hasError: boolean;
  isSuccess: boolean;
}

// ❌ Generics inutili
function log<T>(value: T): void { console.log(value); }

// ❌ Over-annotation
const x: number = 5;
const name: string = "hello";
const items: string[] = ["a", "b", "c"];

// ❌ Non-null assertion senza motivo
const value = data!.property!.nested!;
```

---

Tipi espliciti sulle API pubbliche
strict attivo se possibile
Evitare any, usare unknown quando il tipo non è noto
Usare interface per oggetti e type per union, alias, tuple
Non duplicare tipi: riusa i tipi condivisi
Preferire Partial<>, Pick<>, Omit<> per opzioni e varianti
Esporre valori e funzioni con nomi chiari, consistenti, senza abbreviazioni inutili
Mantenere i default centralizzati in un preset base
Non usare as come scorciatoia per bypassare il type-check
Scrivere funzioni pure quando possibile
Separare config, rendering e helper condivisi
Se un comportamento è comune a più varianti, va nel modulo shared
Se un parametro è opzionale, deve avere un default coerente
Tipizzare bene i return di funzioni esportate quando sono parte dell’API
le varianti devono cambiare solo pochi parametri
niente logica di layout sparsa nei file singoli
la logica comune deve stare in shared.ts
## ✅ Checklist Pre-Commit

Prima di fare commit, verifica:

- [ ] Nessun `any` senza giustificazione commentata
- [ ] Type inference usata dove possibile
- [ ] Discriminated unions per stati complessi
- [ ] Generics solo dove collegano input → output
- [ ] `unknown` per input non verificati
- [ ] Error handling type-safe
- [ ] Nessun non-null assertion (`!`) non necessario
- [ ] Test passano con `strict: true`

---

## 📚 Risorse

- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Total TypeScript](https://totaltypescript.com)
- [Type Challenges](https://github.com/type-challenges/type-challenges)

---

## 🔄 Version History

| Versione | Data | Modifiche |
|----------|------|-----------|
| 1.0.0 | 2026-03-25 | Versione iniziale |

---

> **Ricorda:** Il buon codice TypeScript non è quello con più tipi, è quello con i tipi giusti nel posto giusto.