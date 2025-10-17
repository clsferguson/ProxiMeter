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

// Drag and drop reordering
function initializeDragAndDrop() {
  const grid = document.getElementById('streams-grid');
  if (!grid) {
    return; // No grid on this page
  }
  
  const items = grid.querySelectorAll('.stream-item');
  if (items.length <= 1) {
    return; // No reordering needed for 0 or 1 items
  }
  
  let draggedElement = null;
  
  items.forEach(item => {
    const handle = item.querySelector('.drag-handle');
    if (!handle) return;
    
    // Make item draggable via handle
    handle.addEventListener('mousedown', (e) => {
      item.setAttribute('draggable', 'true');
    });
    
    item.addEventListener('dragstart', (e) => {
      draggedElement = item;
      item.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/html', item.innerHTML);
    });
    
    item.addEventListener('dragend', (e) => {
      item.classList.remove('dragging');
      item.setAttribute('draggable', 'false');
      
      // Save new order to server
      saveStreamOrder();
    });
    
    item.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      
      if (draggedElement && draggedElement !== item) {
        const rect = item.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        
        if (e.clientY < midpoint) {
          grid.insertBefore(draggedElement, item);
        } else {
          grid.insertBefore(draggedElement, item.nextSibling);
        }
      }
    });
  });
}

// Save stream order to server
async function saveStreamOrder() {
  const grid = document.getElementById('streams-grid');
  if (!grid) return;
  
  const items = grid.querySelectorAll('.stream-item');
  const order = Array.from(items).map(item => item.dataset.streamId);
  
  try {
    const response = await fetch('/api/streams/reorder', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ order })
    });
    
    if (!response.ok) {
      console.error('Failed to save stream order');
      // Reload page to restore correct order
      window.location.reload();
    }
  } catch (error) {
    console.error('Error saving stream order:', error);
    // Reload page to restore correct order
    window.location.reload();
  }
}

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeDragAndDrop);
} else {
  initializeDragAndDrop();
}
