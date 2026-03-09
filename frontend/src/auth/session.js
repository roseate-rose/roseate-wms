const USER_KEY = "roseate_wms_user";

function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function getStoredRole() {
  return getStoredUser()?.role || "";
}

function setStoredUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user || null));
}

export { USER_KEY, getStoredRole, getStoredUser, setStoredUser };
