// Advanced Particles System for Crypto Trading Analyzer
// Based on the advanced React particles system, adapted for vanilla JavaScript

class AdvancedParticlesSystem {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.circles = [];
    this.quantity = 120;
    this.staticity = 50;
    this.ease = 50;
    this.size = 0.45;
    this.color = '#00ff9d'; // Primary green color
    this.vx = 0;
    this.vy = 0;
    
    // Mouse tracking
    this.mouse = { x: 0, y: 0 };
    this.canvasSize = { w: 0, h: 0 };
    this.dpr = window.devicePixelRatio || 1;
    this.rafID = null;
    this.resizeTimeout = null;
    
    this.init();
    this.animate();
    this.setupEventListeners();
  }

  init() {
    this.resizeCanvas();
    this.drawParticles();
    
    // Ensure dark background is maintained
    this.ensureDarkBackground();
  }

  ensureDarkBackground() {
    // Keep html and body transparent so the canvas carries the background
    if (document.documentElement) {
      document.documentElement.style.background = 'transparent';
    }
    if (document.body) {
      document.body.style.background = 'transparent';
    }
    
    // Ensure canvas doesn't interfere with background
    if (this.canvas) {
      // The gradient should live on the canvas to appear as one visual plane
      this.canvas.style.background = 'linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%)';
      this.canvas.style.zIndex = '0';
    }
    
    // Force full height coverage for mobile
    if (window.innerWidth <= 768) {
      if (document.documentElement) {
        document.documentElement.style.minHeight = '100vh';
        document.documentElement.style.minHeight = '100dvh';
      }
      if (document.body) {
        document.body.style.minHeight = '100vh';
        document.body.style.minHeight = '100dvh';
      }
    }
  }

  setupEventListeners() {
    // Mouse move tracking
    const handleMouseMove = (event) => {
      const rect = this.canvas.getBoundingClientRect();
      const { w, h } = this.canvasSize;
      const x = event.clientX - rect.left - w / 2;
      const y = event.clientY - rect.top - h / 2;
      const inside = x < w / 2 && x > -w / 2 && y < h / 2 && y > -h / 2;
      if (inside) {
        this.mouse.x = x;
        this.mouse.y = y;
      }
    };

    // Resize handling
    const handleResize = () => {
      if (this.resizeTimeout) {
        clearTimeout(this.resizeTimeout);
      }
      this.resizeTimeout = setTimeout(() => {
        this.resizeCanvas();
        this.ensureDarkBackground();
      }, 200);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('resize', handleResize);

    // Cleanup function
    this.cleanup = () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (this.rafID) {
        window.cancelAnimationFrame(this.rafID);
      }
      if (this.resizeTimeout) {
        clearTimeout(this.resizeTimeout);
      }
    };
  }

  resizeCanvas() {
    this.canvasSize.w = window.innerWidth;
    this.canvasSize.h = window.innerHeight;

    this.canvas.width = this.canvasSize.w * this.dpr;
    this.canvas.height = this.canvasSize.h * this.dpr;
    this.canvas.style.width = `${this.canvasSize.w}px`;
    this.canvas.style.height = `${this.canvasSize.h}px`;
    this.canvas.style.height = `${this.canvasSize.h}px`;
    this.canvas.style.height = `${this.canvasSize.h}dvh`;
    // Maintain gradient background on the canvas layer
    this.canvas.style.background = 'linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%)';
    this.ctx.scale(this.dpr, this.dpr);

    // Clear existing particles and create new ones
    this.circles = [];
    for (let i = 0; i < this.quantity; i++) {
      const circle = this.circleParams();
      this.drawCircle(circle);
    }
  }

  circleParams() {
    const x = Math.floor(Math.random() * this.canvasSize.w);
    const y = Math.floor(Math.random() * this.canvasSize.h);
    const translateX = 0;
    const translateY = 0;
    const pSize = Math.floor(Math.random() * 2) + this.size;
    const alpha = 0;
    const targetAlpha = parseFloat((Math.random() * 0.6 + 0.1).toFixed(1));
    const dx = (Math.random() - 0.5) * 0.1;
    const dy = (Math.random() - 0.5) * 0.1;
    const magnetism = 0.1 + Math.random() * 4;
    
    return {
      x, y, translateX, translateY, size: pSize, alpha, targetAlpha, dx, dy, magnetism
    };
  }

  hexToRgb(hex) {
    hex = hex.replace("#", "");
    if (hex.length === 3) {
      hex = hex.split("").map(char => char + char).join("");
    }
    const hexInt = parseInt(hex, 16);
    const red = (hexInt >> 16) & 255;
    const green = (hexInt >> 8) & 255;
    const blue = hexInt & 255;
    return [red, green, blue];
  }

  drawCircle(circle, update = false) {
    const { x, y, translateX, translateY, size, alpha } = circle;
    const rgb = this.hexToRgb(this.color);
    
    this.ctx.translate(translateX, translateY);
    this.ctx.beginPath();
    this.ctx.arc(x, y, size, 0, 2 * Math.PI);
    this.ctx.fillStyle = `rgba(${rgb.join(", ")}, ${alpha})`;
    this.ctx.fill();
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);

    if (!update) {
      this.circles.push(circle);
    }
  }

  clearContext() {
    this.ctx.clearRect(0, 0, this.canvasSize.w, this.canvasSize.h);
  }

  drawParticles() {
    this.clearContext();
    for (let i = 0; i < this.quantity; i++) {
      const circle = this.circleParams();
      this.drawCircle(circle);
    }
  }

  remapValue(value, start1, end1, start2, end2) {
    const remapped = ((value - start1) * (end2 - start2)) / (end1 - start1) + start2;
    return remapped > 0 ? remapped : 0;
  }

  animate() {
    this.clearContext();
    
    this.circles.forEach((circle, i) => {
      // Handle alpha value based on edge proximity
      const edge = [
        circle.x + circle.translateX - circle.size, // distance from left edge
        this.canvasSize.w - circle.x - circle.translateX - circle.size, // distance from right edge
        circle.y + circle.translateY - circle.size, // distance from top edge
        this.canvasSize.h - circle.y - circle.translateY - circle.size, // distance from bottom edge
      ];
      const closestEdge = edge.reduce((a, b) => Math.min(a, b));
      const remapClosestEdge = parseFloat(
        this.remapValue(closestEdge, 0, 20, 0, 1).toFixed(2)
      );
      
      if (remapClosestEdge > 1) {
        circle.alpha += 0.02;
        if (circle.alpha > circle.targetAlpha) {
          circle.alpha = circle.targetAlpha;
        }
      } else {
        circle.alpha = circle.targetAlpha * remapClosestEdge;
      }

      // Update position
      circle.x += circle.dx + this.vx;
      circle.y += circle.dy + this.vy;
      
      // Apply magnetism towards mouse
      circle.translateX +=
        (this.mouse.x / (this.staticity / circle.magnetism) - circle.translateX) / this.ease;
      circle.translateY +=
        (this.mouse.y / (this.staticity / circle.magnetism) - circle.translateY) / this.ease;

      this.drawCircle(circle, true);

      // Handle particles going out of canvas
      if (
        circle.x < -circle.size ||
        circle.x > this.canvasSize.w + circle.size ||
        circle.y < -circle.size ||
        circle.y > this.canvasSize.h + circle.size
      ) {
        // Remove and create new circle
        this.circles.splice(i, 1);
        const newCircle = this.circleParams();
        this.drawCircle(newCircle);
      }
    });

    this.rafID = window.requestAnimationFrame(() => this.animate());
  }

  // Method to change colors dynamically
  setColors(colors) {
    if (Array.isArray(colors)) {
      this.colors = colors;
    } else {
      this.color = colors;
    }
  }

  // Method to change quantity
  setQuantity(quantity) {
    this.quantity = quantity;
    this.resizeCanvas();
  }

  // Cleanup method
  destroy() {
    if (this.cleanup) {
      this.cleanup();
    }
  }
}

// Initialize particles when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  const canvas = document.createElement('canvas');
  canvas.id = 'particles-canvas';
  canvas.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -1;
    pointer-events: none;
  `;
  
  document.body.appendChild(canvas);
  
  // Create advanced particles system with green theme
  const particlesSystem = new AdvancedParticlesSystem(canvas);
  
  // Set green color palette
  particlesSystem.setColors('#00ff9d');
  
  // Store reference for potential future use
  window.cryptoParticles = particlesSystem;
});
