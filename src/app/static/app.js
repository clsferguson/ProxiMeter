/**
 * ProxiMeter client-side JavaScript
 * Handles header animations, drag-and-drop reordering, and delete confirmations
 */

// Header animation is handled by CSS classes set in templates
// The header has class "header-landing" on landing page
// and "header-playing" on playback page

// Delete confirmation and handler
document.addEventListener('DOMContentLoaded', () => {
  // Attach delete confirmation to all delete buttons
  const deleteButtons = document.querySelectorAll('.delete-btn');
  deleteButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const streamId = btn.dataset.streamId;
      const streamName = btn.dataset.streamName;
      
      if (confirm(`Are you sure you want to delete "${streamName}"?`)) {
        try {
          const response = await fetch(`/api/streams/${streamId}`, {
            method: 'DELETE'
          });
          
          if (response.ok) {
            // Reload page to show updated list
            window.location.reload();
          } else {
            alert('Failed to delete stream. Please try again.');
          }
        } catch (error) {
          console.error('Delete error:', error);
          alert('An error occurred while deleting the stream.');
        }
      }
    });
  });
});

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
