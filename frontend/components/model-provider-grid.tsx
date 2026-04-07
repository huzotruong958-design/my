"use client";

type ProviderCard = {
  id: string;
  label: string;
};

export function ModelProviderGrid({ providers }: { providers: ProviderCard[] }) {
  return (
    <div className="grid">
      {providers.map((provider) => (
        <div key={provider.id} className="panel">
          <div className="eyebrow">{provider.id}</div>
          <h3>{provider.label}</h3>
        </div>
      ))}
    </div>
  );
}
