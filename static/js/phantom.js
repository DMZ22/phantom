/* ============================================
   Phantom.js - Alpine.js Stores & Helpers
   ============================================ */

// ============================================
// Alpine Region Store
// ============================================
document.addEventListener('alpine:init', () => {

  Alpine.store('region', {
    code: localStorage.getItem('phantom_region') || 'IN',

    regions: [
      { code: 'IN', name: 'India', currency: '\u20B9' },
      { code: 'US', name: 'United States', currency: '$' },
      { code: 'GB', name: 'United Kingdom', currency: '\u00A3' },
      { code: 'JP', name: 'Japan', currency: '\u00A5' },
      { code: 'KR', name: 'South Korea', currency: '\u20A9' },
      { code: 'DE', name: 'Germany', currency: '\u20AC' },
      { code: 'FR', name: 'France', currency: '\u20AC' },
      { code: 'AU', name: 'Australia', currency: 'A$' },
      { code: 'CA', name: 'Canada', currency: 'C$' },
      { code: 'BR', name: 'Brazil', currency: 'R$' },
      { code: 'MX', name: 'Mexico', currency: 'MX$' },
      { code: 'IT', name: 'Italy', currency: '\u20AC' },
      { code: 'ES', name: 'Spain', currency: '\u20AC' },
      { code: 'RU', name: 'Russia', currency: '\u20BD' },
    ],

    ticketPrices: {
      IN:  { imax: 450,  gold: 350,  four_dx: 600 },
      US:  { imax: 22,   gold: 18,   four_dx: 30 },
      GB:  { imax: 18,   gold: 15,   four_dx: 25 },
      JP:  { imax: 2500, gold: 2000, four_dx: 3500 },
    },

    // Exchange rates relative to USD (approximate)
    _rates: {
      IN: 83, US: 1, GB: 0.79, JP: 149, KR: 1320,
      DE: 0.92, FR: 0.92, AU: 1.53, CA: 1.36,
      BR: 4.97, MX: 17.1, IT: 0.92, ES: 0.92, RU: 91,
    },

    get currentRegion() {
      return this.regions.find(r => r.code === this.code) || this.regions[0];
    },

    setRegion(code) {
      this.code = code;
      localStorage.setItem('phantom_region', code);
      window.location.reload();
    },

    formatPrice(amount) {
      const region = this.currentRegion;
      return region.currency + parseFloat(amount).toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      });
    },

    getTicketPrice(type) {
      const prices = this.ticketPrices[this.code] || this.ticketPrices['US'];
      return prices[type] || prices['gold'];
    },

    convertFromUSD(usdAmount) {
      const rate = this._rates[this.code] || 1;
      return Math.round(usdAmount * rate * 100) / 100;
    },
  });
});


// ============================================
// HTMX CSRF Configuration
// ============================================
document.addEventListener('htmx:configRequest', (event) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    event.detail.headers['X-CSRFToken'] = csrfToken;
  }
});

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}


// ============================================
// Helper Functions
// ============================================

/**
 * Scroll a horizontal movie row left or right
 */
function scrollRow(el, direction) {
  const container = el.closest('.relative')?.querySelector('.overflow-x-auto')
    || el.closest('.relative')?.querySelector('[class*="overflow-x"]')
    || el.parentElement?.querySelector('.overflow-x-auto');
  if (!container) return;
  const scrollAmount = container.clientWidth * 0.75;
  container.scrollBy({
    left: direction === 'left' ? -scrollAmount : scrollAmount,
    behavior: 'smooth',
  });
}

/**
 * Text-to-speech via Web Speech API
 */
function speakText(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.volume = 1;
  window.speechSynthesis.speak(utterance);
}
