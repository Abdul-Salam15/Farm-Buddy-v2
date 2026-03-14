/**
 * API Client with retry logic and offline support helpers.
 * Used to ensure reliable communication between the Next.js frontend and Django backend.
 */

interface RequestOptions extends RequestInit {
  retries?: number;
  retryDelay?: number;
}

export async function fetchWithRetry(url: string, options: RequestOptions = {}) {
  const { retries = 3, retryDelay = 1000, ...fetchOptions } = options;
  
  let lastError: any;
  
  for (let i = 0; i < retries; i++) {
    try {
      if (!navigator.onLine) {
        throw new Error('Offline');
      }
      
      const response = await fetch(url, fetchOptions);
      
      // If we get a server error (5xx), we might want to retry
      if (!response.ok && response.status >= 500) {
        throw new Error(`Server Error: ${response.status}`);
      }
      
      return response;
    } catch (error) {
      lastError = error;
      console.warn(`Fetch attempt ${i + 1} failed:`, error);
      
      if (i < retries - 1) {
        // Wait before retrying (exponential backoff could be added here)
        await new Promise(resolve => setTimeout(resolve, retryDelay * (i + 1)));
      }
    }
  }
  
  throw lastError;
}

/**
 * Checks if the system is currently offline.
 */
export function isOffline() {
  if (typeof navigator !== 'undefined') {
    return !navigator.onLine;
  }
  return false;
}

/**
 * Queue a request to be sent when the user comes back online.
 * (Simplified version of Background Sync logic)
 */
export function queueOfflineRequest(url: string, data: any) {
  if (typeof window === 'undefined') return;
  
  const queue = JSON.parse(localStorage.getItem('offline_queue') || '[]');
  queue.push({ url, data, timestamp: Date.now() });
  localStorage.setItem('offline_queue', JSON.stringify(queue));
  
  window.addEventListener('online', processQueue, { once: true });
}

async function processQueue() {
  const queue = JSON.parse(localStorage.getItem('offline_queue') || '[]');
  if (queue.length === 0) return;
  
  console.log(`Processing ${queue.length} queued offline requests...`);
  
  for (const item of queue) {
    try {
      await fetch(item.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item.data)
      });
    } catch (e) {
      console.error('Failed to process queued request:', e);
    }
  }
  
  localStorage.removeItem('offline_queue');
}
