"use client";

import { useEffect, useState } from "react";

interface TeamUser {
  id: number;
  email: string;
  role: string;
  active: boolean;
  created_at: string | null;
}

export default function UsersPage() {
  const [users, setUsers] = useState<TeamUser[]>([]);
  const [showInvite, setShowInvite] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer");

  const fetchUsers = async () => {
    const token = localStorage.getItem("access_token");
    const res = await fetch("/api/v1/users/", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setUsers(await res.json());
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const inviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem("access_token");
    await fetch("/api/v1/users/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ email, password, role }),
    });
    setShowInvite(false);
    setEmail("");
    setPassword("");
    fetchUsers();
  };

  const toggleActive = async (userId: number, currentActive: boolean) => {
    const token = localStorage.getItem("access_token");
    await fetch(`/api/v1/users/${userId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ active: !currentActive }),
    });
    fetchUsers();
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Team Members</h1>
        <button onClick={() => setShowInvite(!showInvite)} className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700">
          Invite User
        </button>
      </div>

      {showInvite && (
        <form onSubmit={inviteUser} className="bg-white p-4 rounded-lg shadow mb-6 space-y-3">
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full border rounded px-3 py-2" required />
          <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full border rounded px-3 py-2" required minLength={8} />
          <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full border rounded px-3 py-2">
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
          <button type="submit" className="bg-primary-600 text-white px-4 py-2 rounded">Invite</button>
        </form>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left p-3 text-sm font-medium text-gray-500">Email</th>
              <th className="text-left p-3 text-sm font-medium text-gray-500">Role</th>
              <th className="text-left p-3 text-sm font-medium text-gray-500">Status</th>
              <th className="text-left p-3 text-sm font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="p-3 text-sm">{u.email}</td>
                <td className="p-3 text-sm">
                  <span className={`px-2 py-1 rounded text-xs ${u.role === "admin" ? "bg-purple-100 text-purple-700" : u.role === "editor" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700"}`}>
                    {u.role}
                  </span>
                </td>
                <td className="p-3 text-sm">
                  <span className={`px-2 py-1 rounded text-xs ${u.active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {u.active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="p-3 text-sm">
                  <button onClick={() => toggleActive(u.id, u.active)} className="text-primary-600 hover:underline">
                    {u.active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
