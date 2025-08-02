// static/script.js

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('.read-more').forEach(link => {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        const modal = document.getElementById('readMoreModal');
        document.getElementById('modal-title').innerText = this.dataset.title;
        document.getElementById('modal-content').innerText = this.dataset.content;
        modal.style.display = 'block';
      });
    });
  
    document.querySelector('.close').addEventListener('click', function () {
      document.getElementById('readMoreModal').style.display = 'none';
    });
  
    window.addEventListener('click', function (e) {
      if (e.target === document.getElementById('readMoreModal')) {
        document.getElementById('readMoreModal').style.display = 'none';
      }
    });
  });
  