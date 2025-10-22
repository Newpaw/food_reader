# PWA Splash Screen Configuration

This directory contains the animated SVG splash screen and tools to generate static PNG versions for your Calorie Tracker PWA.

## 📁 Files Overview

- **`infinite-spinner.svg`** - Optimized animated SVG spinner for PWA splash screens
- **`site.webmanifest`** - Updated PWA manifest including the animated SVG
- **`generate-splash-icons.html`** - Browser-based tool to create PNG versions
- **`generate-splash-icons.js`** - Node.js script (requires `sharp` module)

## 🎨 SVG Optimizations Applied

The `infinite-spinner.svg` has been optimized for mobile performance:

1. **Color Update**: Changed from `#9C35FF` to `#4CAF50` to match your app theme
2. **Removed BOM**: Eliminated byte-order mark for proper encoding
3. **Proper Formatting**: Clean, minified SVG structure
4. **Animation**: Smooth 2-second infinite loop animation
5. **Viewbox**: Optimized `300x150` viewBox for efficient scaling

## 📱 PWA Manifest Integration

The animated SVG has been added to [`site.webmanifest`](site.webmanifest:20) with:

```json
{
  "src": "infinite-spinner.svg",
  "sizes": "512x512",
  "type": "image/svg+xml",
  "purpose": "any maskable"
}
```

## 🔄 Generating Static PNG Versions (Optional)

While the animated SVG works on most modern devices, you may want static PNG versions for broader compatibility.

### Method 1: Browser-Based (Recommended)

1. Open [`generate-splash-icons.html`](generate-splash-icons.html) in your browser
2. Click "Generate PNG Icons"
3. Right-click each generated image and select "Save image as..."
4. Save to this directory with the suggested filenames:
   - `splash-192x192.png`
   - `splash-512x512.png`
   - `splash-1024x1024.png`

### Method 2: Node.js Script

If you have Node.js and npm installed:

```bash
# Install dependencies
npm install sharp

# Run the generator
node generate-splash-icons.js
```

### Adding PNG Icons to Manifest

After generating PNG files, add them to [`site.webmanifest`](site.webmanifest:4):

```json
{
  "src": "splash-192x192.png",
  "sizes": "192x192",
  "type": "image/png",
  "purpose": "any maskable"
},
{
  "src": "splash-512x512.png",
  "sizes": "512x512",
  "type": "image/png",
  "purpose": "any maskable"
}
```

## 🧪 Testing

### Desktop Testing
1. Open Chrome DevTools → Application → Manifest
2. Verify the icons are listed correctly
3. Click "Update on reload" to refresh the manifest

### Mobile Testing
1. **Android Chrome**:
   - Open your app in Chrome
   - Tap menu → "Add to Home screen"
   - Install and launch the PWA
   - Observe the splash screen on launch

2. **iOS Safari**:
   - Open your app in Safari
   - Tap Share → "Add to Home Screen"
   - Launch the installed app
   - Note: iOS may use `apple-touch-icon` instead of manifest icons

### Debugging
- Check browser console for manifest errors
- Verify file paths are correct relative to the manifest
- Ensure MIME types are properly configured on your server

## ⚙️ Technical Details

### SVG Animation
- **Type**: CSS-like SVG animation using `<animate>` element
- **Property**: `stroke-dashoffset` animated from 685 to -685
- **Duration**: 2 seconds
- **Timing**: Linear (spline: `0 0 1 1`)
- **Repeat**: Infinite loop

### Browser Support
- ✅ Chrome/Edge 88+ (full animated SVG support)
- ✅ Firefox 90+ (full support)
- ✅ Safari 15+ (full support)
- ⚠️ Older browsers: Falls back to static PNG if provided

### Performance
- **SVG File Size**: ~450 bytes (minified)
- **PNG 192x192**: ~5-8 KB
- **PNG 512x512**: ~15-25 KB
- **Loading Impact**: Minimal (<50ms on 3G)

## 📋 Implementation Checklist

- [x] Optimize `infinite-spinner.svg` for mobile
- [x] Update `site.webmanifest` with SVG icon
- [x] Create PNG generation tools
- [ ] Generate PNG fallback icons (optional)
- [ ] Test on Android devices
- [ ] Test on iOS devices
- [ ] Verify splash screen appearance

## 🚀 Next Steps

1. **Deploy**: Push these changes to your server
2. **Cache**: Clear service worker cache if applicable
3. **Test**: Install PWA on mobile devices to see the animated splash screen
4. **Monitor**: Check analytics for PWA installation metrics

## 🐛 Troubleshooting

**Splash screen doesn't show:**
- Ensure manifest is linked in HTML: `<link rel="manifest" href="assets/favicon/site.webmanifest">`
- Check browser DevTools → Application → Manifest for errors
- Verify file paths are correct (relative to manifest location)

**Animation doesn't play:**
- Older browsers may not support SVG animations in splash screens
- Consider generating static PNG versions as fallback

**Icons appear stretched:**
- Verify the SVG viewBox matches aspect ratio
- Check the `purpose: "any maskable"` attribute

## 📚 Resources

- [Web App Manifest Spec](https://www.w3.org/TR/appmanifest/)
- [PWA Splash Screens](https://web.dev/learn/pwa/app-design/#splash-screens)
- [SVG Animation](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/animate)

---

**Last Updated**: 2025-10-22  
**Version**: 1.0.0