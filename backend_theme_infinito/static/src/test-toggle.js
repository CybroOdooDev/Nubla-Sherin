console.log("Adding debug button...");
const btn = document.createElement("button");
btn.innerHTML = "TOGGLE DARK MODE";
btn.style = "position:fixed;top:10px;left:50%;z-index:999999;padding:20px;background:red;color:white;";
btn.onclick = () => {
    document.body.classList.toggle("dark-mode");
    document.querySelector(".o_web_client").classList.toggle("dark-mode");
    console.log("Toggled dark mode!", document.body.className);
};
document.body.appendChild(btn);
