odoo.define('sidebar_app.SidebarMenu', [], function (require) {
    "use strict";

    import { session } from "@web/session";

    document.addEventListener("click", function (event) {

        // ---- Handle Close Sidebar ----
        if (event.target.closest("#closeSidebar")) {
            const closeBtn = document.getElementById("closeSidebar");
            const openBtn = document.getElementById("openSidebar");
            const sidebarPanel = document.getElementById("sidebar_panel");

            if (closeBtn) closeBtn.style.display = "none";
            if (openBtn) openBtn.style.display = "block";
            if (sidebarPanel) sidebarPanel.style.display = "none";

            const actionManager = document.querySelector(".o_action_manager");
            const topHead = document.querySelector(".top_heading");

            if (actionManager) {
                const actionManagerId = actionManager.dataset.id;
                document.querySelectorAll("div").forEach(div => div.classList.remove(actionManagerId));
                actionManager.classList.remove("sidebar_margin");
            }

            if (topHead) {
                const topHeadId = topHead.dataset.id;
                document.querySelectorAll("div").forEach(div => div.classList.remove(topHeadId));
                topHead.classList.remove("sidebar_margin");
            }
        }

        // ---- Handle Open Sidebar ----
        if (event.target.closest("#openSidebar")) {
            const openBtn = document.getElementById("openSidebar");
            const closeBtn = document.getElementById("closeSidebar");
            const sidebarPanel = document.getElementById("sidebar_panel");

            if (openBtn) openBtn.style.display = "none";
            if (closeBtn) closeBtn.style.display = "block";
            if (sidebarPanel) sidebarPanel.style.display = "block";

            const actionManager = document.querySelector(".o_action_manager");
            const mainNavbar = document.querySelector(".o_main_navbar");
            const topHead = document.querySelector(".top_heading");

            [actionManager, mainNavbar].forEach(el => {
                if (el) el.style.transition = "all .1s linear";
            });

            if (actionManager) {
                const actionManagerId = actionManager.dataset.id;
                document.querySelectorAll("div").forEach(div => div.classList.add(actionManagerId));
                actionManager.classList.add("sidebar_margin");
            }

            if (topHead) {
                const topHeadId = topHead.dataset.id;
                document.querySelectorAll("div").forEach(div => div.classList.add(topHeadId));
                topHead.classList.add("sidebar_margin");
            }
        }

        // ---- Handle Sidebar Menu Click ----
        if (event.target.closest(".sidebar a")) {
            const clickedLink = event.target.closest(".sidebar a");
            const menuItems = document.querySelectorAll(".sidebar a");
            const id = clickedLink.dataset.id;
            const header = document.querySelector("header");

            if (header) {
                header.className = ""; // remove all existing classes
                header.classList.add(id);
            }

            menuItems.forEach(item => item.classList.remove("active"));
            clickedLink.classList.add("active");

            // Close sidebar
            const sidebarPanel = document.getElementById("sidebar_panel");
            const closeBtn = document.getElementById("closeSidebar");
            const openBtn = document.getElementById("openSidebar");

            if (sidebarPanel) sidebarPanel.style.display = "none";
            if (closeBtn) closeBtn.style.display = "none";
            if (openBtn) openBtn.style.display = "block";

            const actionManager = document.querySelector(".o_action_manager");
            const topHead = document.querySelector(".top_heading");

            if (actionManager) {
                const actionManagerId = actionManager.dataset.id;
                document.querySelectorAll("div").forEach(div => div.classList.remove(actionManagerId));
                actionManager.classList.remove("sidebar_margin");
            }

            if (topHead) {
                const topHeadId = topHead.dataset.id;
                document.querySelectorAll("div").forEach(div => div.classList.remove(topHeadId));
                topHead.classList.remove("sidebar_margin");
            }
        }
    });
});
