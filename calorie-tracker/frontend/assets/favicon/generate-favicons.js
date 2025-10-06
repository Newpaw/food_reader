// This script generates favicon files from the embedded SVG source
// Run this in a browser environment

document.addEventListener('DOMContentLoaded', async function() {
  const sizes = [16, 32, 180];
  
  try {
    // SVG content embedded directly to avoid CORS issues
    const svgText = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <!-- Background circle (plate) -->
  <circle cx="50" cy="50" r="45" fill="#f5f5f5" stroke="#4CAF50" stroke-width="5"/>
  
  <!-- Fork (left) -->
  <path d="M35,25 L35,65" stroke="#333" stroke-width="3" stroke-linecap="round"/>
  <path d="M28,25 L28,40" stroke="#333" stroke-width="3" stroke-linecap="round"/>
  <path d="M42,25 L42,40" stroke="#333" stroke-width="3" stroke-linecap="round"/>
  
  <!-- Knife (right) -->
  <path d="M65,25 L65,65" stroke="#333" stroke-width="3" stroke-linecap="round"/>
  <path d="M65,25 C75,30 75,40 65,45" fill="none" stroke="#333" stroke-width="3" stroke-linecap="round"/>
  
  <!-- Calorie indicator (small circle in the middle) -->
  <circle cx="50" cy="50" r="10" fill="#FF5722"/>
</svg>`;
    
    // Create a container to display results
    const container = document.createElement('div');
    container.style.padding = '20px';
    document.body.appendChild(container);
    
    const title = document.createElement('h1');
    title.textContent = 'Favicon Generator';
    container.appendChild(title);
    
    const results = document.createElement('div');
    container.appendChild(results);
    
    // Function to convert SVG to PNG
    async function svgToPng(svgText, size) {
      return new Promise((resolve) => {
        const img = new Image();
        img.onload = function() {
          const canvas = document.createElement('canvas');
          canvas.width = size;
          canvas.height = size;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, size, size);
          resolve(canvas.toDataURL('image/png'));
        };
        img.src = 'data:image/svg+xml;base64,' + btoa(svgText);
      });
    }
    
    // Generate PNGs for each size
    for (const size of sizes) {
      const pngDataUrl = await svgToPng(svgText, size);
      
      // Create download link
      const filename = size === 180 ? 'apple-touch-icon.png' : `favicon-${size}x${size}.png`;
      const link = document.createElement('a');
      link.href = pngDataUrl;
      link.download = filename;
      link.textContent = `Download ${filename}`;
      link.style.display = 'block';
      link.style.margin = '10px 0';
      results.appendChild(link);
      
      // Display preview
      const preview = document.createElement('img');
      preview.src = pngDataUrl;
      preview.style.border = '1px solid #ccc';
      preview.style.marginRight = '10px';
      results.appendChild(preview);
      
      results.appendChild(document.createElement('hr'));
    }
    
    // Generate site.webmanifest content
    const webmanifest = {
      name: "Calorie Tracker",
      short_name: "CalTracker",
      icons: [
        {
          src: "favicon-16x16.png",
          sizes: "16x16",
          type: "image/png"
        },
        {
          src: "favicon-32x32.png",
          sizes: "32x32",
          type: "image/png"
        },
        {
          src: "apple-touch-icon.png",
          sizes: "180x180",
          type: "image/png"
        }
      ],
      theme_color: "#4CAF50",
      background_color: "#ffffff",
      display: "standalone"
    };
    
    const webmanifestBlob = new Blob(
      [JSON.stringify(webmanifest, null, 2)], 
      {type: 'application/json'}
    );
    const webmanifestUrl = URL.createObjectURL(webmanifestBlob);
    
    const webmanifestLink = document.createElement('a');
    webmanifestLink.href = webmanifestUrl;
    webmanifestLink.download = 'site.webmanifest';
    webmanifestLink.textContent = 'Download site.webmanifest';
    webmanifestLink.style.display = 'block';
    webmanifestLink.style.margin = '10px 0';
    results.appendChild(webmanifestLink);
    
    // Note about favicon.ico
    const note = document.createElement('p');
    note.innerHTML = '<strong>Note:</strong> For favicon.ico, you\'ll need to combine the 16x16 and 32x32 PNGs using an ICO converter tool or service.';
    results.appendChild(note);
    
    // Instructions
    const instructions = document.createElement('div');
    instructions.innerHTML = `
      <h2>Instructions:</h2>
      <ol>
        <li>Click each download link to save the files</li>
        <li>Move all files to your favicon directory</li>
        <li>For favicon.ico, use an online converter with the 16x16 and 32x32 PNG files</li>
      </ol>
    `;
    container.appendChild(instructions);
    
  } catch (error) {
    console.error('Error generating favicons:', error);
    document.body.innerHTML = `<div style="color: red; padding: 20px;">
      Error generating favicons: ${error.message}
    </div>`;
  }
});