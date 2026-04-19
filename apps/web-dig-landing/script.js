// 모바일 메뉴 토글
const menuToggle = document.getElementById("menuToggle");
const navMenu = document.getElementById("navMenu");

menuToggle.addEventListener("click", function () {
  navMenu.classList.toggle("active");
});

// 메뉴 클릭 시 모바일 메뉴 닫기
const navLinks = navMenu.querySelectorAll("a");
navLinks.forEach((link) => {
  link.addEventListener("click", function () {
    navMenu.classList.remove("active");
  });
});

// 문의 폼 제출 처리
const contactForm = document.getElementById("contactForm");
const formMessage = document.getElementById("formMessage");

contactForm.addEventListener("submit", function (e) {
  e.preventDefault();
  formMessage.textContent = "문의가 정상적으로 접수되었습니다. 빠르게 연락드리겠습니다.";
  contactForm.reset();
});