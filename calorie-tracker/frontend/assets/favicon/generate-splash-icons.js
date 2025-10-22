/**
 * Generate PNG splash screen icons from SVG
 * 
 * This script creates static PNG snapshots of the animated spinner SVG
 * for use as PWA splash screen icons on devices that don't support animated SVGs.
 * 
 * Usage:
 * 1. Install dependencies: npm install sharp
 * 2. Run: node generate-splash-icons.js
 */

const fs = require('fs');
const path = require('path');

// Check if sharp is available
let sharp;
try {
  sharp = require('sharp');
} catch (err) {
  console.error('Error: sharp module not found.');
  console.error('Please install it by running: npm install sharp');
  process.exit(1);
}

const svgPath = path.join(__dirname, 'infinite-spinner.svg');
const svgContent = fs.readFileSync(svgPath, 'utf8');

// Define sizes for different devices
const sizes = [
  { size: 192, name: 'splash-192x192.png' },
  { size: 512, name: 'splash-512x512.png' },
  { size: 1024, name: 'splash-1024x1024.png' }
];

async function generateIcons() {
  console.log('Generating splash screen icons...\n');
  
  for (const config of sizes) {
    try {
      const outputPath = path.join(__dirname, config.name);
      
      // Create PNG from SVG with white background
      await sharp(Buffer.from(svgContent))
        .resize(config.size, config.size, {
          fit: 'contain',
          background: { r: 255, g: 255, b: 255, alpha: 1 }
        })
        .png()
        .toFile(outputPath);
      
      const stats = fs.statSync(outputPath);
      console.log(`✓ Generated ${config.name} (${config.size}x${config.size}) - ${(stats.size / 1024).toFixed(2)} KB`);
    } catch (error) {
      console.error(`✗ Error generating ${config.name}:`, error.message);
    }
  }
  
  console.log('\n✓ All splash screen icons generated successfully!');
  console.log('\nNext steps:');
  console.log('1. Add these icons to your site.webmanifest');
  console.log('2. Test the PWA installation on mobile devices');
}

generateIcons().catch(err => {
  console.error('Error generating icons:', err);
  process.exit(1);
});