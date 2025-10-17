/**
 * ProxiMeter client-side JavaScript
 * Handles header animations, drag-and-drop reordering, and delete confirmations
 */

// Header animation state management
function updateHeaderState(isPlaying) {
  const header = document.getElementById('app-header');
  if (!header) return;
  
  if (isPlaying) {
    header.classList.remove('header-landing');
    header.classList.add('header-playing');
  } else {
    header.classList.remove('header-playing');
    header.classList.add('header-landing');
  }
}

// Initialize header state based on current page
document.addEventListener('DOMContentLoaded', () => {
  const isPlaybackPage = window.location.pathname.includes('/play/');
  updateHeaderState(isPlaybackPage);
});

// Delete confirmation
function confirmDelete(streamName) {
  return confirm(`Are you sure you want to delete "${streamName}"?`);
}

// Drag and drop reordering (to be implemented in T046)
function initializeDragAndDrop() {
  // TODO: Implement drag-and-drop in T046
  console.log('Drag-and-drop not yet implemented');
}

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeDragAndDrop);
} else {
  initializeDragAndDrop();
}
