/**
 * Image Optimizer for Calorie Tracker
 * 
 * This module provides client-side image optimization functionality:
 * - Resizes large images to a reasonable size (max 1200px width/height)
 * - Compresses images to reduce file size while maintaining quality
 * - Maintains aspect ratio during resizing
 * - Works on both mobile and desktop browsers
 */

const ImageOptimizer = {
  // Default configuration
  config: {
    maxWidth: 1200,
    maxHeight: 1200,
    quality: 0.85,  // JPEG quality (0.8-0.9 recommended for good balance)
    format: 'image/jpeg',
    thumbnailWidth: 300,
    thumbnailHeight: 250
  },

  /**
   * Optimize an image file by resizing and compressing it
   * @param {File} file - The original image file from input
   * @param {Object} options - Optional configuration overrides
   * @returns {Promise<Blob>} - Promise resolving to the optimized image blob
   */
  async optimizeImage(file, options = {}) {
    // Merge default config with provided options
    const settings = { ...this.config, ...options };
    
    // Create a promise to handle the image processing
    return new Promise((resolve, reject) => {
      // Check if the file is an image
      if (!file || !file.type.startsWith('image/')) {
        reject(new Error('Invalid file type. Please select an image.'));
        return;
      }

      // Create a FileReader to read the file
      const reader = new FileReader();
      
      // Set up the FileReader onload event
      reader.onload = (event) => {
        // Create an image element to load the file data
        const img = new Image();
        
        // Set up the image onload event
        img.onload = () => {
          // Calculate new dimensions while maintaining aspect ratio
          const dimensions = this._calculateDimensions(img.width, img.height, settings.maxWidth, settings.maxHeight);
          
          // Create a canvas element for resizing
          const canvas = document.createElement('canvas');
          canvas.width = dimensions.width;
          canvas.height = dimensions.height;
          
          // Get the canvas context and draw the resized image
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, dimensions.width, dimensions.height);
          
          // Convert the canvas to a Blob with the specified quality
          canvas.toBlob((blob) => {
            if (blob) {
              // Log optimization results
              console.log(`Image optimized: ${(file.size / 1024).toFixed(2)}KB → ${(blob.size / 1024).toFixed(2)}KB (${Math.round((1 - blob.size / file.size) * 100)}% reduction)`);
              resolve(blob);
            } else {
              reject(new Error('Failed to optimize image'));
            }
          }, settings.format, settings.quality);
        };
        
        // Handle image loading errors
        img.onerror = () => {
          reject(new Error('Failed to load image'));
        };
        
        // Set the image source to the FileReader result
        img.src = event.target.result;
      };
      
      // Handle FileReader errors
      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };
      
      // Read the file as a data URL
      reader.readAsDataURL(file);
    });
  },

  /**
   * Create a thumbnail preview for display
   * @param {File|Blob} file - The image file or blob
   * @param {Object} options - Optional configuration overrides
   * @returns {Promise<string>} - Promise resolving to the thumbnail data URL
   */
  async createThumbnail(file, options = {}) {
    // Merge default config with provided options
    const settings = { ...this.config, ...options };
    
    return new Promise((resolve, reject) => {
      // Create a FileReader to read the file
      const reader = new FileReader();
      
      // Set up the FileReader onload event
      reader.onload = (event) => {
        // Create an image element to load the file data
        const img = new Image();
        
        // Set up the image onload event
        img.onload = () => {
          // Calculate thumbnail dimensions while maintaining aspect ratio
          const dimensions = this._calculateDimensions(
            img.width, 
            img.height, 
            settings.thumbnailWidth, 
            settings.thumbnailHeight
          );
          
          // Create a canvas element for the thumbnail
          const canvas = document.createElement('canvas');
          canvas.width = dimensions.width;
          canvas.height = dimensions.height;
          
          // Get the canvas context and draw the thumbnail
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, dimensions.width, dimensions.height);
          
          // Convert the canvas to a data URL
          const dataUrl = canvas.toDataURL(settings.format, 0.7); // Lower quality for thumbnails
          resolve(dataUrl);
        };
        
        // Handle image loading errors
        img.onerror = () => {
          reject(new Error('Failed to load image for thumbnail'));
        };
        
        // Set the image source to the FileReader result
        img.src = event.target.result;
      };
      
      // Handle FileReader errors
      reader.onerror = () => {
        reject(new Error('Failed to read file for thumbnail'));
      };
      
      // Read the file as a data URL
      reader.readAsDataURL(file);
    });
  },

  /**
   * Calculate new dimensions while maintaining aspect ratio
   * @param {number} width - Original width
   * @param {number} height - Original height
   * @param {number} maxWidth - Maximum allowed width
   * @param {number} maxHeight - Maximum allowed height
   * @returns {Object} - Object containing new width and height
   * @private
   */
  _calculateDimensions(width, height, maxWidth, maxHeight) {
    // Check if resizing is needed
    if (width <= maxWidth && height <= maxHeight) {
      return { width, height }; // No resizing needed
    }
    
    // Calculate aspect ratio
    const aspectRatio = width / height;
    
    // Calculate new dimensions based on constraints
    let newWidth = maxWidth;
    let newHeight = maxWidth / aspectRatio;
    
    // If height is still too large, constrain by height instead
    if (newHeight > maxHeight) {
      newHeight = maxHeight;
      newWidth = maxHeight * aspectRatio;
    }
    
    // Return new dimensions as integers
    return {
      width: Math.round(newWidth),
      height: Math.round(newHeight)
    };
  },

  /**
   * Check if an image needs optimization based on size
   * @param {File} file - The image file to check
   * @returns {boolean} - True if the image should be optimized
   */
  shouldOptimize(file) {
    // Skip optimization for small files (less than 100KB)
    if (file.size < 100 * 1024) {
      return false;
    }
    
    return true;
  },

  /**
   * Convert a File to a Blob with the same type
   * @param {File} file - The file to convert
   * @returns {Promise<Blob>} - Promise resolving to a Blob
   */
  fileToBlob(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const blob = new Blob([reader.result], { type: file.type });
        resolve(blob);
      };
      reader.onerror = reject;
      reader.readAsArrayBuffer(file);
    });
  }
};

// Export the ImageOptimizer object
window.ImageOptimizer = ImageOptimizer;