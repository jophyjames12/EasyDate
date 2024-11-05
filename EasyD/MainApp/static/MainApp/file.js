document.addEventListener('DOMContentLoaded', function() {
    const authContainer = document.querySelector('.auth-container');
    // Add a small timeout for a fade-in effect
    setTimeout(() => {
        authContainer.classList.add('show');
    }, 100);

});

document.addEventListener('DOMContentLoaded', function() {          //event listeners for slider buttons
    document.querySelector('.right-arrow').addEventListener('click', nextSlide);
    document.querySelector('.left-arrow').addEventListener('click', prevSlide);
});


function toggleMenu() {
    const dropdown = document.getElementById("dropdown");
    dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
}

let currentSlide = 0; // Track the current slide index

function showSlide(index) {
    const slides = document.querySelectorAll('.slide');
    const totalSlides = slides.length;

    // Update the slide index within bounds
    if (index >= totalSlides) {
        currentSlide = 0;
    } else if (index < 0) {
        currentSlide = totalSlides - 1;
    } else {
        currentSlide = index;
    }

    console.log("Showing slide:", currentSlide);

    // Move the slider-content container to show the current slide
    const sliderContent = document.querySelector('.slider-content');
    if (sliderContent) {
        sliderContent.style.transform = `translateX(-${currentSlide * 100}%)`;
    } else {
        console.error("Slider content container not found.");
    }
}

function nextSlide() {
    showSlide(currentSlide + 1);
}

function prevSlide() {
    showSlide(currentSlide - 1);
}


