const API_URL = "http://127.0.0.1:8000";
const state = { token: localStorage.getItem("helpdesk_token"), refreshToken: localStorage.getItem("helpdesk_refresh_token"), user: null, categories: [], technicians: [], adminTickets: [], dashboardTickets: [], dashboardFilter: null, managedUsers: [], notifications: [], notificationsInitialized: false, notificationTimer: null, adminPage: 1, adminTotalPages: 1, slaPolicies: [] };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

function setMessage(element, text = "") {
  element.textContent = text;
}

function showToast(text) {
  const toast = $("#toast");
  toast.textContent = text;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 3200);
}

async function request(path, options = {}, retrying = false) {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (response.status === 401 && state.refreshToken && !retrying && path !== "/auth/refresh") {
    const refreshResponse = await fetch(`${API_URL}/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: state.refreshToken }) });
    if (refreshResponse.ok) {
      const refreshed = await refreshResponse.json();
      state.token = refreshed.access_token;
      state.refreshToken = refreshed.refresh_token;
      localStorage.setItem("helpdesk_token", state.token);
      localStorage.setItem("helpdesk_refresh_token", state.refreshToken);
      return request(path, options, true);
    }
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Não foi possível concluir a operação.");
  return data;
}

function showDashboard() {
  $("#auth-view").classList.add("hidden");
  $("#admin-view").classList.add("hidden");
  $("#users-view").classList.add("hidden");
  $("#dashboard-view").classList.remove("hidden");
  $("#logout-button").classList.remove("hidden");
  $("#home-button").classList.remove("hidden");
  $("#profile-button").classList.remove("hidden");
  $("#notifications-button").classList.remove("hidden");
  $("#user-label").textContent = state.user.email;
  $("#welcome-name").textContent = state.user.name;
  $("#admin-button").classList.toggle("hidden", state.user.role !== "ADMIN");
  $$('[data-open-ticket]').forEach((button) => button.classList.toggle("hidden", state.user.role !== "USER"));
  $("#new-ticket-button").classList.toggle("hidden", state.user.role !== "USER");
  loadDashboard();
}

function showAuth() {
  stopNotificationPolling();
  $("#auth-view").classList.remove("hidden");
  $("#dashboard-view").classList.add("hidden");
  $("#admin-view").classList.add("hidden");
  $("#users-view").classList.add("hidden");
  $("#admin-button").classList.add("hidden");
  $("#home-button").classList.add("hidden");
  $("#profile-button").classList.add("hidden");
  $("#notifications-button").classList.add("hidden");
  $("#notifications-panel").classList.add("hidden");
  $("#logout-button").classList.add("hidden");
  $("#user-label").textContent = "";
}

async function pollNotifications() {
  if (!state.token) return;
  try {
    const notifications = await request("/notifications");
    const previousIds = new Set(state.notifications.map((notification) => notification.id));
    if (state.notificationsInitialized) {
      const newNotifications = notifications.filter((notification) => !previousIds.has(notification.id));
      newNotifications.forEach((notification) => showToast(notification.title));
      if (newNotifications.length) {
        loadDashboard();
        if (!$("#admin-view").classList.contains("hidden")) loadAdminTickets();
      }
    }
    state.notifications = notifications;
    state.notificationsInitialized = true;
    renderNotifications();
  } catch (error) { /* Notification polling must not interrupt the main portal. */ }
}

function renderNotifications() {
  const unread = state.notifications.filter((notification) => !notification.is_read);
  $("#notification-badge").textContent = unread.length;
  $("#notification-badge").classList.toggle("hidden", unread.length === 0);
  $("#notifications-list").innerHTML = state.notifications.length
    ? state.notifications.map((notification) => `<article class="notification-item ${notification.is_read ? "read" : ""}" data-notification-id="${notification.id}"><strong>${escapeHtml(notification.title)}</strong><p>${escapeHtml(notification.message)}</p><time>${new Date(notification.created_at).toLocaleString("pt-BR")}</time></article>`).join("")
    : '<p class="notifications-empty">Nenhuma notificação nova.</p>';
}

async function markAllNotificationsRead() {
  await request("/notifications/read-all", { method: "PATCH" });
  state.notifications.forEach((notification) => { notification.is_read = true; });
  renderNotifications();
}

async function clearNotifications() {
  await request("/notifications", { method: "DELETE" });
  state.notifications = [];
  renderNotifications();
}

function startNotificationPolling() {
  if (state.notificationTimer) clearInterval(state.notificationTimer);
  pollNotifications();
  state.notificationTimer = setInterval(pollNotifications, 5000);
}

function stopNotificationPolling() {
  if (state.notificationTimer) clearInterval(state.notificationTimer);
  state.notificationTimer = null;
  state.notifications = [];
  state.notificationsInitialized = false;
}

function showAdmin() {
  if (state.user?.role !== "ADMIN") return;
  $("#dashboard-view").classList.add("hidden");
  $("#users-view").classList.add("hidden");
  $("#admin-view").classList.remove("hidden");
  loadAdminTickets();
  loadSlaPolicies();
}

async function loadSlaPolicies() {
  setMessage($("#sla-message"));
  try {
    state.slaPolicies = await request("/sla");
    renderSlaPolicies();
  } catch (error) {
    setMessage($("#sla-message"), error.message);
  }
}

function renderSlaPolicies() {
  const names = { LOW: "Baixa", MEDIUM: "Normal", HIGH: "Alta", CRITICAL: "Crítica" };
  $("#sla-list").innerHTML = state.slaPolicies.map((policy) => `<label class="sla-item"><span><strong>${names[policy.priority]}</strong><small>Prazo em horas</small></span><input type="number" min="1" max="720" value="${policy.resolution_hours}" data-sla-priority="${policy.priority}" /></label>`).join("");
}

async function updateSlaPolicy(event) {
  if (!event.target.dataset.slaPriority || event.key !== "Enter") return;
  try {
    const updated = await request(`/sla/${event.target.dataset.slaPriority}`, { method: "PATCH", body: JSON.stringify({ resolution_hours: Number(event.target.value) }) });
    state.slaPolicies = state.slaPolicies.map((policy) => policy.priority === updated.priority ? updated : policy);
    showToast("Prazo de SLA atualizado.");
  } catch (error) {
    setMessage($("#sla-message"), error.message);
    loadSlaPolicies();
  }
}

function showUsers() {
  if (state.user?.role !== "ADMIN") return;
  $("#dashboard-view").classList.add("hidden");
  $("#admin-view").classList.add("hidden");
  $("#users-view").classList.remove("hidden");
  loadUsers();
}

async function loadUsers() {
  setMessage($("#user-message"));
  try {
    state.managedUsers = await request("/users");
    renderUsers(state.managedUsers);
  } catch (error) { setMessage($("#user-message"), error.message); }
}

function renderUsers(users) {
  $("#users-list").innerHTML = users.map((user) => `<article class="user-row" data-user-id="${user.id}"><div><strong>${escapeHtml(user.name)}</strong><small>#${user.id}</small></div><div>${escapeHtml(user.email)}</div><span class="user-status">${user.role} · ${user.is_active ? "Ativo" : "Inativo"}</span><div class="user-actions"><button class="button button-ghost user-edit" type="button">Editar</button><button class="danger-button user-delete" type="button">Excluir</button></div></article>`).join("") || '<div class="admin-empty">Nenhum usuário cadastrado.</div>';
}

async function createManagedUser(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  setMessage($("#user-message"));
  try {
    await request("/users", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
    event.target.reset();
    showToast("Usuário criado.");
    loadUsers();
  } catch (error) { setMessage($("#user-message"), error.message); }
}

async function updateManagedUser(event) {
  const row = event.target.closest("[data-user-id]");
  if (!row) return;
  const userId = row.dataset.userId;
  const payload = event.target.classList.contains("user-role")
    ? { role: event.target.value }
    : { is_active: event.target.textContent === "Ativar" };
  try {
    await request(`/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) });
    showToast("Usuário atualizado.");
    loadUsers();
  } catch (error) { setMessage($("#user-message"), error.message); }
}

function openManagedUserEdit(userId) {
  const user = state.managedUsers.find((item) => item.id === Number(userId));
  if (!user) return;
  const form = $("#managed-user-edit-form");
  form.user_id.value = user.id;
  form.name.value = user.name;
  form.email.value = user.email;
  form.role.value = user.role;
  form.is_active.value = String(user.is_active);
  setMessage($("#managed-user-message"));
  $("#managed-user-modal").classList.remove("hidden");
}

async function saveManagedUser(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    await request(`/users/${form.get("user_id")}`, { method: "PATCH", body: JSON.stringify({ name: form.get("name"), email: form.get("email"), role: form.get("role"), is_active: form.get("is_active") === "true" }) });
    $("#managed-user-modal").classList.add("hidden");
    showToast("Usuário atualizado.");
    loadUsers();
  } catch (error) { setMessage($("#managed-user-message"), error.message); }
}

async function deleteManagedUser(event) {
  const button = event.target.closest(".user-delete");
  if (!button) return;
  const row = button.closest("[data-user-id]");
  if (!window.confirm(`Excluir o usuário ${row.querySelector("strong").textContent}?`)) return;
  try {
    await request(`/users/${row.dataset.userId}`, { method: "DELETE" });
    showToast("Usuário excluído.");
    loadUsers();
  } catch (error) { setMessage($("#user-message"), error.message); }
}

function openProfile() {
  $("#profile-form [name='name']").value = state.user.name;
  $("#profile-email").value = state.user.email;
  setMessage($("#profile-message"));
  $("#profile-modal").classList.remove("hidden");
}

async function updateProfile(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  setMessage($("#profile-message"));
  try {
    state.user = await request("/auth/me", { method: "PATCH", body: JSON.stringify({ name: form.get("name") }) });
    $("#user-label").textContent = state.user.email;
    $("#welcome-name").textContent = state.user.name;
    $("#profile-modal").classList.add("hidden");
    showToast("Nome atualizado com sucesso.");
  } catch (error) { setMessage($("#profile-message"), error.message); }
}

async function loadDashboard() {
  try {
    const [ticketsPage, categories, stats] = await Promise.all([
      request("/tickets"),
      request("/categories"),
      request("/dashboard"),
    ]);
    state.categories = categories;
    renderCategories();
    state.dashboardTickets = ticketsPage.items;
    renderFilteredDashboardTickets();
    $("#stat-open").textContent = stats.open;
    $("#stat-progress").textContent = stats.in_progress;
    $("#stat-closed").textContent = stats.closed;
    $("#stat-overdue").textContent = stats.overdue;
  } catch (error) {
    showToast(error.message);
  }
}

function renderFilteredDashboardTickets() {
  const filteredTickets = state.dashboardFilter
    ? state.dashboardTickets.filter((ticket) => ticket.status === state.dashboardFilter)
    : state.dashboardTickets;
  renderTickets(filteredTickets);
  const activeFilter = state.dashboardFilter;
  $$(".stat-filter").forEach((card) => card.classList.toggle("active", card.dataset.statusFilter === activeFilter));
  $("#clear-ticket-filter").classList.toggle("hidden", !activeFilter);
  $("#tickets-heading").textContent = activeFilter ? `Chamados ${statusFilterLabels[activeFilter].toLowerCase()}` : "Meus chamados";
}

const statusFilterLabels = { OPEN: "abertos", IN_PROGRESS: "em atendimento", CLOSED: "fechados" };

async function loadAdminTickets() {
  setMessage($("#admin-message"));
  try {
    const [ticketsPage, users] = await Promise.all([request(`/tickets?page=${state.adminPage}&limit=20`), request("/users")]);
    state.adminTickets = ticketsPage.items;
    state.adminTotalPages = ticketsPage.pages;
    state.technicians = users.filter((user) => user.role === "TECHNICIAN" && user.is_active);
    renderAdminTickets();
  } catch (error) {
    setMessage($("#admin-message"), error.message);
  }
}

function renderAdminTickets() {
  const search = $("#admin-search").value.trim().toLowerCase();
  const status = $("#admin-status-filter").value;
  const priority = $("#admin-priority-filter").value;
  const tickets = state.adminTickets.filter((ticket) => {
    const matchesText = !search || `${ticket.title} ${ticket.description}`.toLowerCase().includes(search);
    return matchesText && (!status || ticket.status === status) && (!priority || ticket.priority === priority);
  });
  const list = $("#admin-tickets-list");
  $("#admin-page-label").textContent = `Página ${state.adminPage} de ${state.adminTotalPages}`;
  $("#admin-previous").disabled = state.adminPage <= 1;
  $("#admin-next").disabled = state.adminPage >= state.adminTotalPages;
  if (!tickets.length) {
    list.innerHTML = '<div class="admin-empty">Nenhum chamado corresponde aos filtros.</div>';
    return;
  }
  const header = '<div class="admin-ticket admin-ticket-header"><span>Chamado</span><span>Status</span><span>Prioridade</span><span>Técnico responsável</span><span></span></div>';
  list.innerHTML = header + tickets.map((ticket) => `<article class="admin-ticket" data-ticket-id="${ticket.id}"><div class="admin-ticket-title"><strong>#${ticket.id} · ${escapeHtml(ticket.title)}</strong><span>${escapeHtml(ticket.description.slice(0, 90))}</span><button class="text-button admin-conversation" data-ticket-id="${ticket.id}" type="button">Ver conversa →</button></div><select class="admin-status" aria-label="Status do chamado ${ticket.id}">${statusOptions(ticket.status)}</select><span class="status ${ticket.priority.toLowerCase()}">${priorityLabels[ticket.priority]}</span><select class="admin-technician" aria-label="Técnico do chamado ${ticket.id}"><option value="">Não atribuído</option>${state.technicians.map((technician) => `<option value="${technician.id}" ${ticket.technician_id === technician.id ? "selected" : ""}>${escapeHtml(technician.name)}</option>`).join("")}</select><div class="admin-actions"><button class="danger-button admin-delete" type="button" title="Excluir chamado">Excluir</button></div></article>`).join("");
}

const priorityLabels = { LOW: "Baixa", MEDIUM: "Normal", HIGH: "Alta", CRITICAL: "Crítica" };
function statusOptions(selected) {
  const adminStatuses = ["OPEN", "IN_PROGRESS", "WAITING_USER", "CLOSED"];
  const options = Object.entries(labels)
    .filter(([value]) => adminStatuses.includes(value))
    .map(([value, label]) => `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`);
  if (selected === "RESOLVED") options.push('<option value="RESOLVED" selected disabled>Resolvido (pelo técnico)</option>');
  return options.join("");
}

async function handleAdminChange(event) {
  const ticketElement = event.target.closest("[data-ticket-id]");
  if (!ticketElement) return;
  const ticketId = ticketElement.dataset.ticketId;
  try {
    if (event.target.classList.contains("admin-status")) {
      await request(`/tickets/${ticketId}/status`, { method: "PATCH", body: JSON.stringify({ status: event.target.value }) });
      showToast("Status atualizado.");
    }
    if (event.target.classList.contains("admin-technician")) {
      await request(`/tickets/${ticketId}/assign`, { method: "PATCH", body: JSON.stringify({ technician_id: event.target.value ? Number(event.target.value) : null }) });
      showToast(event.target.value ? "Técnico atribuído." : "Técnico removido.");
    }
    loadAdminTickets();
  } catch (error) {
    setMessage($("#admin-message"), error.message);
    loadAdminTickets();
  }
}

async function handleAdminDelete(event) {
  const button = event.target.closest(".admin-delete");
  if (!button) return;
  const ticketElement = button.closest("[data-ticket-id]");
  if (!window.confirm(`Excluir o chamado #${ticketElement.dataset.ticketId}?`)) return;
  try {
    await request(`/tickets/${ticketElement.dataset.ticketId}`, { method: "DELETE" });
    showToast("Chamado excluído.");
    loadAdminTickets();
  } catch (error) {
    setMessage($("#admin-message"), error.message);
  }
}

function renderCategories() {
  const select = $("#category-select");
  select.innerHTML = '<option value="">Selecione uma categoria</option>';
  state.categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category.id;
    option.textContent = category.name;
    select.appendChild(option);
  });
}

const labels = { OPEN: "Aberto", IN_PROGRESS: "Em atendimento", WAITING_USER: "Aguardando você", RESOLVED: "Resolvido", CLOSED: "Fechado" };
function renderTickets(tickets) {
  const list = $("#tickets-list");
  if (!tickets.length) {
    list.innerHTML = '<div class="empty-state"><span class="empty-icon">✦</span><h3>Nenhum chamado por aqui</h3><p>Quando precisar de ajuda, abra seu primeiro chamado.</p><button class="button button-secondary" type="button" data-open-ticket>Fazer um pedido</button></div>';
    bindOpenButtons();
    return;
  }
  list.innerHTML = tickets.map((ticket) => `<article class="ticket-item"><div><h3>${escapeHtml(ticket.title)}</h3><p>${escapeHtml(ticket.description.slice(0, 100))}${ticket.description.length > 100 ? "..." : ""}</p><button class="text-button ticket-conversation" data-ticket-id="${ticket.id}" type="button">Ver conversa →</button></div><div class="ticket-meta"><span class="status ${ticket.status.toLowerCase()} ${ticket.priority.toLowerCase()}">${labels[ticket.status] || ticket.status}</span>${state.user?.role === "TECHNICIAN" && ticket.status !== "CLOSED" ? `<select class="technician-status" data-ticket-id="${ticket.id}" aria-label="Atualizar status do chamado ${ticket.id}">${technicianStatusOptions(ticket.status)}</select>` : ""}<span class="ticket-date">${new Date(ticket.created_at).toLocaleDateString("pt-BR")}</span></div></article>`).join("");
}

function technicianStatusOptions(selected) {
  return Object.entries(labels).map(([value, label]) => `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`).join("");
}

async function updateTechnicianStatus(event) {
  if (!event.target.classList.contains("technician-status")) return;
  const ticketId = event.target.dataset.ticketId;
  let resolutionNote;
  if (event.target.value === "RESOLVED") {
    resolutionNote = window.prompt("Descreva o que foi feito neste chamado:");
    if (!resolutionNote || resolutionNote.trim().length < 3) {
      showToast("Informe pelo menos 3 caracteres sobre a solução.");
      loadDashboard();
      return;
    }
  }
  try {
    await request(`/tickets/${ticketId}/status`, { method: "PATCH", body: JSON.stringify({ status: event.target.value, resolution_note: resolutionNote }) });
    showToast("Status atualizado.");
    loadDashboard();
  } catch (error) {
    showToast(error.message);
    loadDashboard();
  }
}

async function openComments(ticketId) {
  const ticket = state.dashboardTickets.find((item) => item.id === Number(ticketId)) || state.adminTickets.find((item) => item.id === Number(ticketId));
  if (!ticket) return;
  $("#comments-title").textContent = `#${ticket.id} · ${ticket.title}`;
  $("#detail-status").textContent = labels[ticket.status] || ticket.status;
  $("#detail-status").className = `status ${ticket.status.toLowerCase()}`;
  $("#detail-priority").textContent = priorityLabels[ticket.priority] || ticket.priority;
  $("#detail-priority").className = `status ${ticket.priority.toLowerCase()}`;
  $("#detail-date").textContent = new Date(ticket.created_at).toLocaleDateString("pt-BR");
  $("#detail-technician").textContent = ticket.technician_id ? `Técnico #${ticket.technician_id}` : "Não atribuído";
  $("#detail-description").textContent = ticket.description;
  $("#comments-modal").classList.remove("hidden");
  $("#comments-list").innerHTML = "Carregando conversa...";
  $("#comment-form").classList.toggle("hidden", ticket.status === "CLOSED");
  $("#comment-form").dataset.ticketId = ticket.id;
  try {
    const [comments, audit] = await Promise.all([
      request(`/tickets/${ticket.id}/comments`),
      request(`/tickets/${ticket.id}/audit`),
    ]);
    $("#audit-list").innerHTML = audit.length ? audit.map((entry) => `<div class="audit-item"><strong>${auditLabels[entry.action] || entry.action}</strong><span>${new Date(entry.created_at).toLocaleString("pt-BR")}</span></div>`).join("") : '<p class="audit-empty">Nenhuma alteração registrada.</p>';
    $("#comments-list").innerHTML = comments.length ? comments.map((comment) => { const ownMessage = comment.user_id === state.user.id; return `<div class="comment-item ${ownMessage ? "comment-own" : "comment-other"}"><div class="comment-header"><strong>${ownMessage ? "Você" : escapeHtml(comment.author_name)}</strong><span>${new Date(comment.created_at).toLocaleString("pt-BR")}</span></div><p>${escapeHtml(comment.content)}</p></div>`; }).join("") : '<p class="comments-empty">Ainda não há mensagens. Seja o primeiro a responder.</p>';
  } catch (error) {
    $("#comments-list").textContent = error.message;
  }
}

const auditLabels = { CREATE: "Chamado criado", UPDATE: "Chamado atualizado", STATUS_CHANGE: "Status alterado", ASSIGN: "Técnico atribuído", UNASSIGN: "Técnico removido", COMMENT: "Comentário adicionado", DELETE: "Chamado excluído" };

async function sendComment(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const ticketId = event.target.dataset.ticketId;
  setMessage($("#comment-message"));
  try {
    await request(`/tickets/${ticketId}/comments`, { method: "POST", body: JSON.stringify({ content: form.get("content") }) });
    event.target.reset();
    showToast("Resposta enviada.");
    openComments(ticketId);
  } catch (error) { setMessage($("#comment-message"), error.message); }
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

async function login(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  setMessage($("#auth-message"));
  try {
    const body = new URLSearchParams({ username: form.get("email"), password: form.get("password") });
    const response = await fetch(`${API_URL}/auth/login`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Email ou senha inválidos.");
    state.token = data.access_token;
    state.refreshToken = data.refresh_token;
    localStorage.setItem("helpdesk_token", state.token);
    localStorage.setItem("helpdesk_refresh_token", state.refreshToken);
    state.user = await request("/auth/me");
      startNotificationPolling();
    showDashboard();
  } catch (error) {
    setMessage($("#auth-message"), error.message);
  }
}

async function register(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  setMessage($("#auth-message"));
  try {
    await request("/auth/register", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
    $("[data-auth-tab='login']").click();
    $("#login-form [name='email']").value = form.get("email");
    showToast("Conta criada. Agora entre no portal.");
  } catch (error) {
    setMessage($("#auth-message"), error.message);
  }
}

function openModal() {
  $("#ticket-modal").classList.remove("hidden");
  $("#ticket-form [name='title']").focus();
}
function closeModal() { $("#ticket-modal").classList.add("hidden"); setMessage($("#ticket-message")); }
function bindOpenButtons() { $$('[data-open-ticket]').forEach((button) => button.addEventListener("click", openModal)); }

async function createTicket(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  setMessage($("#ticket-message"));
  try {
    await request("/tickets", { method: "POST", body: JSON.stringify({ title: form.get("title"), description: form.get("description"), priority: form.get("priority"), category_id: Number(form.get("category_id")) }) });
    event.target.reset();
    closeModal();
    showToast("Chamado enviado com sucesso.");
    loadDashboard();
  } catch (error) { setMessage($("#ticket-message"), error.message); }
}

$$("[data-auth-tab]").forEach((tab) => tab.addEventListener("click", () => {
  $$('[data-auth-tab]').forEach((item) => item.classList.remove("active"));
  tab.classList.add("active");
  $("#login-form").classList.toggle("hidden", tab.dataset.authTab !== "login");
  $("#register-form").classList.toggle("hidden", tab.dataset.authTab !== "register");
  setMessage($("#auth-message"));
}));
$("#login-form").addEventListener("submit", login);
$("#register-form").addEventListener("submit", register);
$("#ticket-form").addEventListener("submit", createTicket);
$("#close-modal").addEventListener("click", closeModal);
$("#new-ticket-button").addEventListener("click", openModal);
$("#refresh-button").addEventListener("click", loadDashboard);
$("#clear-ticket-filter").addEventListener("click", () => { state.dashboardFilter = null; renderFilteredDashboardTickets(); });
$$('[data-status-filter]').forEach((card) => card.addEventListener("click", () => { state.dashboardFilter = card.dataset.statusFilter; renderFilteredDashboardTickets(); }));
$("#admin-button").addEventListener("click", showAdmin);
$("#users-button").addEventListener("click", showUsers);
$("#back-admin-button").addEventListener("click", showAdmin);
$("#managed-user-form").addEventListener("submit", createManagedUser);
$("#users-list").addEventListener("change", updateManagedUser);
$("#users-list").addEventListener("click", (event) => {
  if (event.target.classList.contains("user-edit")) openManagedUserEdit(event.target.closest("[data-user-id]").dataset.userId);
  if (event.target.classList.contains("user-delete")) deleteManagedUser(event);
});
$("#managed-user-edit-form").addEventListener("submit", saveManagedUser);
$("#close-managed-user-modal").addEventListener("click", () => $("#managed-user-modal").classList.add("hidden"));
$("#managed-user-modal").addEventListener("click", (event) => { if (event.target.id === "managed-user-modal") $("#managed-user-modal").classList.add("hidden"); });
$("#home-button").addEventListener("click", showDashboard);
$("#profile-button").addEventListener("click", openProfile);
$("#back-dashboard-button").addEventListener("click", showDashboard);
$("#admin-refresh-button").addEventListener("click", loadAdminTickets);
$("#admin-previous").addEventListener("click", () => { if (state.adminPage > 1) { state.adminPage -= 1; loadAdminTickets(); } });
$("#admin-next").addEventListener("click", () => { if (state.adminPage < state.adminTotalPages) { state.adminPage += 1; loadAdminTickets(); } });
$("#sla-list").addEventListener("keydown", updateSlaPolicy);
$("#admin-search").addEventListener("input", renderAdminTickets);
$("#admin-status-filter").addEventListener("change", renderAdminTickets);
$("#admin-priority-filter").addEventListener("change", renderAdminTickets);
$("#admin-tickets-list").addEventListener("change", handleAdminChange);
$("#admin-tickets-list").addEventListener("click", handleAdminDelete);
$("#logout-button").addEventListener("click", async () => { if (state.refreshToken && state.token) await request("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: state.refreshToken }) }).catch(() => {}); localStorage.removeItem("helpdesk_token"); localStorage.removeItem("helpdesk_refresh_token"); state.token = null; state.refreshToken = null; state.user = null; showAuth(); });
$("#notifications-button").addEventListener("click", () => { $("#notifications-panel").classList.toggle("hidden"); renderNotifications(); });
$("#close-notifications").addEventListener("click", () => $("#notifications-panel").classList.add("hidden"));
$("#mark-all-read").addEventListener("click", () => markAllNotificationsRead().catch((error) => showToast(error.message)));
$("#clear-notifications").addEventListener("click", () => clearNotifications().catch((error) => showToast(error.message)));
$("#notifications-list").addEventListener("click", async (event) => { const item = event.target.closest("[data-notification-id]"); if (!item) return; const notification = state.notifications.find((value) => value.id === Number(item.dataset.notificationId)); if (notification && !notification.is_read) { await request(`/notifications/${notification.id}/read`, { method: "PATCH" }); notification.is_read = true; renderNotifications(); } });
$("#ticket-modal").addEventListener("click", (event) => { if (event.target.id === "ticket-modal") closeModal(); });
$("#tickets-list").addEventListener("click", (event) => { const button = event.target.closest(".ticket-conversation"); if (button) openComments(button.dataset.ticketId); });
$("#tickets-list").addEventListener("change", updateTechnicianStatus);
$("#admin-tickets-list").addEventListener("click", (event) => { const button = event.target.closest(".admin-conversation"); if (button) openComments(button.dataset.ticketId); });
$("#close-comments-modal").addEventListener("click", () => $("#comments-modal").classList.add("hidden"));
$("#comments-modal").addEventListener("click", (event) => { if (event.target.id === "comments-modal") $("#comments-modal").classList.add("hidden"); });
$("#comment-form").addEventListener("submit", sendComment);
$("#close-profile-modal").addEventListener("click", () => $("#profile-modal").classList.add("hidden"));
$("#profile-modal").addEventListener("click", (event) => { if (event.target.id === "profile-modal") $("#profile-modal").classList.add("hidden"); });
$("#profile-form").addEventListener("submit", updateProfile);
bindOpenButtons();

if (state.token) request("/auth/me").then((user) => { state.user = user; showDashboard(); startNotificationPolling(); }).catch(() => { localStorage.removeItem("helpdesk_token"); localStorage.removeItem("helpdesk_refresh_token"); state.token = null; state.refreshToken = null; });
