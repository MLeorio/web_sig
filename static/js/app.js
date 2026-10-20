// app.js — comportements partagés par toutes les pages :
//   - menu de navigation mobile (hamburger)
//   - modale de confirmation générique (attribut data-confirm)

document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.nav-toggle');
  var navbar = document.querySelector('.navbar');
  if (toggle && navbar) {
    toggle.addEventListener('click', function () {
      navbar.classList.toggle('is-open');
    });
  }

  setupConfirmModals();
});

// Intercepte la soumission de tout <form data-confirm="..."> et affiche une
// modale avant d'envoyer réellement la requête. Utilisé pour les
// confirmations de modification et de suppression (voir le cahier des
// charges : jamais de suppression directe sans confirmation explicite).
function setupConfirmModals() {
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (form.dataset.confirmed === 'true') {
        return; // déjà confirmé par l'utilisateur, on laisse partir la requête
      }
      event.preventDefault();
      var isDanger = /supprim/i.test(form.dataset.confirm) || form.querySelector('.btn-danger');
      openConfirmModal(form.dataset.confirm, isDanger, function () {
        form.dataset.confirmed = 'true';
        form.submit();
      });
    });
  });
}

function openConfirmModal(message, isDanger, onConfirm) {
  var backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';

  var titleText = isDanger ? '⚠ Confirmation requise' : '💾 Confirmation';
  var confirmLabel = isDanger ? 'Confirmer' : 'Confirmer';
  var confirmClass = isDanger ? 'btn-danger' : 'btn-primary';

  backdrop.innerHTML =
    '<div class="modal" role="dialog" aria-modal="true">' +
      '<h3' + (isDanger ? ' style="color:var(--danger);"' : '') + '>' + titleText + '</h3>' +
      '<p></p>' +
      '<div class="actions">' +
        '<button type="button" class="btn btn-ghost btn-sm" data-action="cancel">Annuler</button>' +
        '<button type="button" class="btn ' + confirmClass + ' btn-sm" data-action="confirm">' + confirmLabel + '</button>' +
      '</div>' +
    '</div>';

  // le message vient des données de l'application (jamais de saisie libre
  // utilisateur non filtrée) mais on l'assigne en textContent par prudence.
  backdrop.querySelector('p').textContent = message;

  function close() { document.body.removeChild(backdrop); }

  backdrop.querySelector('[data-action="cancel"]').addEventListener('click', close);
  backdrop.querySelector('[data-action="confirm"]').addEventListener('click', function () {
    close();
    onConfirm();
  });
  backdrop.addEventListener('click', function (event) {
    if (event.target === backdrop) close();
  });

  document.body.appendChild(backdrop);
}
