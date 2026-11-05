# UI Architecture Rules: Unslop System

You must strictly evaluate all UI code against the 'heydamir/unslop' guidelines before generating or modifying any React/Tailwind/HTML elements.

## 🚫 Forbidden AI-Slop Visual Patterns
- No unprompted purple-to-blue linear gradients (`from-purple-600 to-blue-500`).
- No generic, unconfigured shadcn/Tailwind default layouts.
- No centered hero sections with an oversized email signup box.
- No predictable, perfectly uniform 3-column feature grids.
- No random glassmorphic cards (`bg-white/10 backdrop-blur-md`) unless explicitly requested.
- No emojis used as standalone dashboard icons.

## ✨ Mandatory Design Requirements
1. **Asymmetric Structural Layouts:** Vary card widths, introduce side panels, or use off-center balance grids.
2. **Explicit Color Tokens:** Use exact raw Tailwind neutral pairings for canvas surfaces (`bg-slate-50`, `bg-zinc-900`) and choose precisely *one* crisp brand accent color.
3. **Intentional Typography Hierarchy:** Use clear font weight contrasts; body text must use high-readability tracking.
4. **Real Asset Footprints:** Use structured icon libraries (e.g., Lucide-react) or actual image placeholders instead of gray layout squares.

## 🔄 Multi-Pass UI Refinement Loop
When building or updating a component, execute your edits in this strict order:
1. Spacing & Grid Hierarchy
2. Typography & Color Weights
3. Visual Assets & Component Icons
4. Micro-interactions & Smooth Transitions
