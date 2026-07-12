"use client";

import { useEffect, useState } from "react";

interface Plan {
  id: number;
  name: string;
  monthly_fee: number;
  features: Record<string, any>;
}

interface Subscription {
  plan_id: number;
  plan_name: string;
  monthly_fee: number;
  features: Record<string, any>;
  status: string;
  usage: Record<string, number>;
}

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    fetch("/api/v1/billing/subscription", { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(setSubscription);
    fetch("/api/v1/billing/plans", { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(setPlans);
  }, []);

  const upgrade = async (planId: number) => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(`/api/v1/billing/upgrade?plan_id=${planId}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) window.location.reload();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Billing</h1>

      {subscription && (
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-lg font-semibold mb-2">Current Plan: {subscription.plan_name}</h2>
          <p className="text-3xl font-bold text-primary-600">${subscription.monthly_fee}/mo</p>
          <div className="mt-4">
            <h3 className="font-medium mb-2">Usage This Month</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>Queries: {subscription.usage?.total_queries || 0}</div>
              <div>Tokens: {subscription.usage?.total_tokens || 0}</div>
            </div>
          </div>
        </div>
      )}

      <h2 className="text-xl font-bold mb-4">Available Plans</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {plans.map((plan) => (
          <div key={plan.id} className={`bg-white p-6 rounded-lg shadow border-2 ${plan.id === subscription?.plan_id ? "border-primary-500" : "border-transparent"}`}>
            <h3 className="text-lg font-bold">{plan.name}</h3>
            <p className="text-2xl font-bold text-primary-600 my-2">${plan.monthly_fee}<span className="text-sm text-gray-500">/mo</span></p>
            <ul className="text-sm space-y-1 mb-4">
              <li>Sites: {plan.features?.sites || 0}</li>
              <li>Queries/mo: {(plan.features?.queries_per_month || 0).toLocaleString()}</li>
              <li>Chunks: {(plan.features?.chunks || 0).toLocaleString()}</li>
            </ul>
            {plan.id !== subscription?.plan_id && (
              <button onClick={() => upgrade(plan.id)} className="w-full bg-primary-600 text-white py-2 rounded hover:bg-primary-700">
                Upgrade
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
