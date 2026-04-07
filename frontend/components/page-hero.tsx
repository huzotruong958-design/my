"use client";

type PageHeroProps = {
  eyebrow: string;
  title: string;
  description: string;
};

export function PageHero({ eyebrow, title, description }: PageHeroProps) {
  return (
    <div className="hero">
      <div className="eyebrow">{eyebrow}</div>
      <h1 style={{ margin: 0 }}>{title}</h1>
      <p className="muted">{description}</p>
    </div>
  );
}
