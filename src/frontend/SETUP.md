# Frontend Setup Instructions

This frontend is set up with React, TypeScript, Tailwind CSS, and shadcn/ui structure.

## Project Structure

- **Components**: Located in `src/components/ui/` following shadcn conventions
- **Path Aliases**: `@/` maps to `src/` directory
- **Styling**: Tailwind CSS with custom configuration for shadcn/ui

## Why `/components/ui` folder?

The `/components/ui` folder is the standard location for shadcn/ui components. This structure:
- Follows shadcn conventions for easy component management
- Allows using `npx shadcn@latest add [component]` to add new components
- Keeps UI components separate from application components
- Makes it easy to identify which components are from shadcn/ui

## Installed Dependencies

### Production Dependencies
- `react` & `react-dom` - React framework
- `lucide-react` - Icon library
- `framer-motion` - Animation library
- `@radix-ui/react-dialog` - Dialog component primitives
- `@radix-ui/react-tooltip` - Tooltip component primitives

### Development Dependencies
- `typescript` - TypeScript support
- `tailwindcss` - CSS framework
- `tailwindcss-animate` - Animation utilities for Tailwind
- `vite` - Build tool
- `@vitejs/plugin-react` - Vite React plugin

## Running the Project

```bash
# Install dependencies (if not already installed)
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Component Usage

The `PromptInputBox` component is located at `src/components/ui/ai-prompt-box.tsx` and can be imported as:

```tsx
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
```

A demo implementation is available in `src/components/demo.tsx` and is currently used in `src/App.tsx`.

## Configuration Files

- `tailwind.config.js` - Tailwind CSS configuration with shadcn/ui theme
- `postcss.config.js` - PostCSS configuration
- `vite.config.ts` - Vite configuration with path aliases
- `tsconfig.app.json` - TypeScript configuration with path aliases
- `components.json` - shadcn/ui configuration

## Adding New shadcn Components

To add new shadcn/ui components:

```bash
npx shadcn@latest add [component-name]
```

This will automatically add the component to `src/components/ui/` following the shadcn structure.

