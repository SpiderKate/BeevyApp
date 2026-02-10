# Color Theme Creation Guide

## Overview
The CSS has been refactored to use a central theme system in `base.css`. All pages inherit the base styles and colors, making it easy to create new color themes.

## How Base CSS Organization Works

### Structure:
1. **base.css** - Contains:
   - `:root` CSS variables (all theme colors)
   - Global animations
   - Common component styles
   - Layout structures
   - Utility classes

2. **Page-specific CSS files** - Contain only:
   - Page-specific layouts
   - Component customizations for that page
   - NO duplicate variables or animations
   - NO duplicate button/form styling

### Files:
- `base.css` - **Main foundation** (always required)
- `art_detail.css` - Art detail page specific styles
- `create_art.css` - Create artwork page
- `draw.css` - Drawing canvas page
- `password.css` - Password reset page
- `register.css` - Register/login page
- `settings.css` - Settings/profile page
- `shop.css` - Shop/gallery page
- `styles.css` - **DEPRECATED** (can be removed)
- `styles_test.css` - **DEPRECATED** (test file, can be removed)

## Creating a New Color Theme

### Step 1: Create a new CSS file
```
/static/css/theme-dark.css  (or your theme name)
```

### Step 2: Define theme variables

```css
/* Dark Theme Example */
:root {
    /* Only override the colors you want to change */
    --primary-bg: #2d2d44;
    --primary-bg-light: #3d3d54;
    --primary-bg-dark: #1d1d34;
    --primary-text: #e0e0e0;
    --accent-color: #ff9800;
    --accent-light: #ffb74d;
    
    /* Glass & Transparency - adjust for this theme */
    --glass-bg: rgb(45 45 68 / 15%);
    --glass-bg-light: rgb(45 45 68 / 20%);
    --glass-border: rgb(255 255 255 / 15%);
    --glass-border-light: rgb(255 255 255 / 30%);
    
    /* Other colors */
    --details: #9c8fc7;
}

/* Override body background if needed */
body {
    background: radial-gradient(circle at top left, #3d3d54, #2d2d44 70%);
}
```

### Step 3: Apply in your HTML templates

In your base template (e.g., `base.html`):

```html
<head>
    <!-- Base styles (ALWAYS required) -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/base.css') }}">
    
    <!-- OPTIONAL: Load your theme after base.css -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/theme-dark.css') }}">
    
    <!-- Page-specific styles (if needed) -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/art_detail.css') }}">
</head>
```

## Available CSS Variables

### Primary Colors
```css
--primary-bg           /* Main purple background */
--primary-bg-light     /* Lighter variant */
--primary-bg-dark      /* Darker variant */
--primary-text         /* Main golden/yellow text */
--accent-color         /* Accent yellow */
--accent-light         /* Lighter accent */
```

### Glass & Transparency
```css
--glass-bg             /* Semi-transparent background */
--glass-bg-light       /* Lighter glass bg */
--glass-border         /* Glass border color */
--glass-border-light   /* Lighter glass border */
--glass-blur           /* Blur effect (don't change) */
```

### Spacing & Animation
```css
--transition-speed     /* Animation duration (0.3s) */
--radius              /* Large border radius (18px) */
--radius-md           /* Medium (15px) */
--radius-sm           /* Small (12px) */
--radius-xs           /* Extra small (10px) */
--details             /* Secondary purple color */
--text-outline        /* Text outline effect */
```

## Available Global Animations

All animations are defined in `base.css` and can be used in any theme:

```css
@keyframes float         /* Vertical floating motion */
@keyframes floatHex      /* Hex element floating */
@keyframes fadeIn        /* Fade with slide up */
@keyframes buzz          /* Subtle scale and rotation */
@keyframes bee-flap      /* Bee wing flapping */
@keyframes bee-pull      /* Bee pulling sidebar */
```

Usage example:
```css
.my-element {
    animation: float 6s ease-in-out infinite;
}
```

## Common CSS Variables Used in Page Files

Page-specific files use these common patterns:

```css
/* Forms and inputs */
var(--primary-bg)              /* Button background */
var(--primary-text)            /* Text color */
var(--accent-color)            /* Highlights */

/* Containers */
var(--glass-bg)                /* Card backgrounds */
var(--glass-blur)              /* Backdrop filter */
var(--radius)                  /* Large components */
var(--radius-sm)               /* Buttons */
var(--radius-xs)               /* Inputs */

/* Effects */
var(--transition-speed)        /* Smooth transitions */
rgb(247 235 78 / 50%)         /* Accent with opacity */
```

## Theme Examples

### Cyberpunk Theme
```css
:root {
    --primary-bg: #0a0e27;
    --primary-text: #00ff88;
    --accent-color: #ff0080;
    --glass-bg: rgb(0 255 136 / 8%);
}
body {
    background: radial-gradient(circle at top left, #1a1e4e, #0a0e27 70%);
}
```

### Pastel Theme
```css
:root {
    --primary-bg: #dab6fc;
    --primary-text: #5b21b6;
    --accent-color: #fbbf24;
    --glass-bg: rgb(255 255 255 / 20%);
}
body {
    background: radial-gradient(circle at top left, #e9d5ff, #dab6fc 70%);
}
```

### Forest Theme
```css
:root {
    --primary-bg: #1f3a1f;
    --primary-text: #c7ff9a;
    --accent-color: #7cfc00;
    --glass-bg: rgb(124 252 0 / 8%);
}
body {
    background: radial-gradient(circle at top left, #2d5a2d, #1f3a1f 70%);
}
```

## Tips & Best Practices

1. **Start Small**: Only override the color variables you need to change
2. **Test Contrast**: Ensure text is readable on your new background
3. **Use the Same Variables**: Reuse `--glass-bg`, `--accent-color`, etc. instead of hardcoding colors
4. **Mobile First**: Test on mobile devices
5. **Keep Animations**: Don't override animations - they're globally defined
6. **Lazy Load Themes**: Load theme CSS only when needed with JavaScript

## Adding a Theme Switcher

To allow users to switch themes dynamically:

```javascript
function switchTheme(themeName) {
    const link = document.getElementById('theme-link');
    if (!link) {
        const newLink = document.createElement('link');
        newLink.id = 'theme-link';
        newLink.rel = 'stylesheet';
        document.head.appendChild(newLink);
    }
    
    const link = document.getElementById('theme-link');
    link.href = `/static/css/theme-${themeName}.css`;
    localStorage.setItem('selectedTheme', themeName);
}

// On page load, restore previously selected theme
window.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('selectedTheme');
    if (saved) switchTheme(saved);
});
```

## Deprecation Notice

The following files are no longer needed and can be removed:
- ✗ `styles.css` - Old styles file
- ✗ `styles_test.css` - Test file

All functionality has been consolidated into `base.css` and page-specific files.

## Need Help?

When creating a theme:
1. Copy an existing color scheme from this guide
2. Create your CSS file in `/static/css/`
3. Test in all pages to ensure consistency
4. Check mobile responsiveness
5. Verify text contrast and readability
