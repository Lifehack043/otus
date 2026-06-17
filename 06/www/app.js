document.addEventListener('DOMContentLoaded', function() {
    console.log('Страница загружена');
    
    const links = document.querySelectorAll('nav a');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            console.log('Переход по ссылке:', this.href);
        });
    });
});
