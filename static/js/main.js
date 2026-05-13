function copyText(elementId) {
  const box = document.getElementById(elementId);
  const btn = box.querySelector('.copy-btn');
  const text = box.innerText.replace(btn ? btn.innerText : '', '').trim();
  navigator.clipboard.writeText(text).then(() => {
    showAlert('✅ Copiado al portapapeles', 'success');
  });
}

function showAlert(msg, type) {
  const container = document.getElementById('alert-container');
  if (!container) return;
  container.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
  setTimeout(() => { container.innerHTML = ''; }, 3500);
}

function publicarInstagram(listingId) {
  fetch(`/publicar/${listingId}`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.ok) showAlert('✅ Publicado en Instagram exitosamente', 'success');
      else showAlert('❌ Error al publicar: ' + data.error, 'error');
    })
    .catch(() => showAlert('❌ Error de conexión', 'error'));
}

function generarVideo(listingId) {
  const btn = document.getElementById('btn-video');
  btn.disabled = true;
  btn.textContent = '⏳ Iniciando...';
  document.getElementById('video-progress').style.display = 'block';

  fetch(`/video/${listingId}`, { method: 'POST' })
    .then(r => r.json())
    .then(() => pollVideo(listingId))
    .catch(() => showAlert('❌ Error al iniciar video', 'error'));
}

function pollVideo(listingId) {
  const fill = document.getElementById('progress-fill');
  const status = document.getElementById('video-status');
  let progress = 5;

  const interval = setInterval(() => {
    fetch(`/video/status/${listingId}`)
      .then(r => r.json())
      .then(data => {
        if (data.status === 'done') {
          clearInterval(interval);
          fill.style.width = '100%';
          status.textContent = '✅ Video listo para descargar';
          document.getElementById('video-download').style.display = 'block';
          document.getElementById('video-link').href = `/generated/videos/${listingId}.mp4`;
        } else if (data.status === 'error') {
          clearInterval(interval);
          status.textContent = '❌ Error al generar video';
          showAlert('❌ Error al renderizar el video', 'error');
        } else {
          progress = Math.min(progress + 8, 90);
          fill.style.width = progress + '%';
          status.textContent = 'Renderizando video reel...';
        }
      })
      .catch(() => clearInterval(interval));
  }, 2500);
}
