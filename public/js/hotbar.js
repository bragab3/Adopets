// public/js/hotbar.js
document.addEventListener("DOMContentLoaded", async () => {
  const usuarioLocal = JSON.parse(localStorage.getItem("usuarioLogado") || "null");
  const paginaInicial = usuarioLocal ? "homelogada.html" : "home.html";

  // 1. Padroniza a Hotbar em todas as páginas
  const listaNav = document.querySelector(".lista-menu-nav");
  if (listaNav) {
    listaNav.innerHTML = `
      <li class="item-menu-nav"><a href="${paginaInicial}">Início</a></li>
      <li class="item-menu-nav"><a href="catalogo.html">Adote</a></li>
      <li class="item-menu-nav"><a href="animais_perdidos.html">Animais Perdidos</a></li>

      <li class="item-menu-nav dropdown">
        <a href="#" class="dropbtn">Recursos</a>
        <ul class="dropdown-content">
          <li><a href="calendario.html">Calendário</a></li>
          <li><a href="blog.html">Blog</a></li>
        </ul>
      </li>

      <li class="item-menu-nav"><a href="sobre-nos.html" id="link-sobre-nos">Sobre Nós</a></li>
    `;

    // 2. Comportamento de rolar a página até "Nossa História" (.sessao-sobre)
    const linkSobreNos = document.getElementById("link-sobre-nos");
    if (linkSobreNos) {
      linkSobreNos.addEventListener("click", (e) => {
        e.preventDefault();
        const sessaoSobre = document.querySelector(".sessao-sobre");
        if (sessaoSobre) {
          // Se já está na Home, apenas rola suavemente para baixo
          sessaoSobre.scrollIntoView({ behavior: "smooth" });
        } else {
          // Se está em outra página, vai para a Home e aciona a rolagem
          window.location.href = `${paginaInicial}#sobre`;
        }
      });
    }
  }

  // Se veio de outra página clicando em "Sobre Nós" (#sobre), rola suavemente ao carregar
  if (window.location.hash === "#sobre") {
    const sessaoSobre = document.querySelector(".sessao-sobre");
    if (sessaoSobre) {
      setTimeout(() => {
        sessaoSobre.scrollIntoView({ behavior: "smooth" });
      }, 150);
    }
  }

  // 3. Sincroniza nome e foto do usuário logado na Hotbar
  const headers = {};
  if (usuarioLocal && usuarioLocal.id) {
    headers["x-usuario-id"] = String(usuarioLocal.id);
  }

  try {
    const res = await fetch("/api/usuario-dados", {
      credentials: "same-origin",
      headers
    });

    if (res.ok) {
      const u = await res.json();
      localStorage.setItem("usuarioLogado", JSON.stringify(u));

      document.querySelectorAll(".nome-usuario").forEach(el => {
        el.textContent = u.nome;
      });
      document.querySelectorAll(".foto-usuario").forEach(el => {
        el.src = u.foto || "Images/cliente.png";
      });
    } else {
      document.querySelectorAll(".nome-usuario").forEach(el => {
        if (window.location.pathname.endsWith("home.html") || window.location.pathname === "/") {
          el.textContent = "Entrar";
        }
      });
    }
  } catch (err) {
    console.error("Erro ao sincronizar hotbar:", err);
  }

  // 4. Configura o botão de Sair na mini-navbar
  const linksSair = document.querySelectorAll('#mini-navbar a[href="home.html"], #logout-btn');
  linksSair.forEach(link => {
    link.addEventListener("click", async (e) => {
      e.preventDefault();
      localStorage.removeItem("usuarioLogado");
      await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
      window.location.href = "login.html";
    });
  });
});