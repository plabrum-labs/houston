import {
  Body,
  Container,
  Head,
  Html,
  Preview,
  Section,
  Text,
  Hr,
  Tailwind,
  Button as ReactEmailButton,
} from '@react-email/components';
import * as React from 'react';

// Almanac palette — paper + ink + brass. Mirrors the in-app
// `[data-theme="almanac"]` tokens defined in frontend/src/index.css.
const tailwindConfig = {
  theme: {
    extend: {
      colors: {
        paper: '#f1e8d4',
        'paper-warm': '#f6eedb',
        'paper-card': '#faf2de',
        'paper-deep': '#e6dbc1',
        ink: '#0d1f2c',
        'ink-soft': '#1e3344',
        'ink-muted': '#5b6976',
        brass: '#b8845c',
        'brass-deep': '#8b5e3a',
        rust: '#a85a3a',
        // Aliases so existing markup keeps rendering:
        dark: '#0d1f2c',
        mid: '#5b6976',
        'light-border': '#d8cdb2',
        'footer-muted': '#8b7d62',
        'footer-subtle': '#a89b80',
      },
      fontFamily: {
        // Web-safe fallbacks first so most clients render predictably.
        // Fraunces/Newsreader come through where the client supports
        // them (most modern Apple/Gmail web clients).
        serif: ["'Fraunces'", 'Georgia', "'Times New Roman'", 'serif'],
        body: ["'Newsreader'", 'Georgia', "'Times New Roman'", 'serif'],
        sans: ['Arial', 'Helvetica', 'sans-serif'],
        mono: ["'Space Mono'", 'ui-monospace', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
} as const;

interface BaseLayoutProps {
  preview: string;
  children: React.ReactNode;
  footerNote?: string;
}

export function BaseLayout({ preview, children, footerNote }: BaseLayoutProps) {
  return (
    <Html lang="en">
      <Tailwind config={tailwindConfig}>
        <Head />
        <Preview>{preview}</Preview>
        <Body className="bg-paper m-0 p-0 font-body">
          <table role="presentation" width="100%" cellPadding={0} cellSpacing={0} className="bg-paper">
            <tbody>
              <tr>
                <td align="center" className="py-10 px-5">
                  <Container className="max-w-[560px] w-full">

                    {/* Wordmark */}
                    <Section className="pb-8 text-center">
                      <Text className="font-serif text-[28px] text-ink tracking-tight m-0">
                        Marlin Survey
                      </Text>
                      <div className="mx-auto mt-3 h-px w-16 bg-brass" />
                    </Section>

                    {/* Main card */}
                    <Section className="bg-paper-card rounded-[2px] border border-light-border px-10 py-12">
                      {children}

                      {/* Sign-off */}
                      <Text className="font-body text-[15px] text-ink mt-8 mb-0">
                        Fair winds,<br />
                        <span className="text-brass-deep">The Marlin Survey Team</span>
                      </Text>
                    </Section>

                    {/* Footer */}
                    <Section className="pt-8 text-center">
                      <Text className="font-mono text-[10px] text-footer-muted uppercase tracking-[0.22em] m-0 mb-1">
                        &copy; 2026 Marlin Survey
                      </Text>
                      <Text className="font-sans text-[11px] text-footer-subtle m-0">
                        {footerNote ?? "You're receiving this because you have a Marlin Survey account."}
                      </Text>
                    </Section>

                  </Container>
                </td>
              </tr>
            </tbody>
          </table>
        </Body>
      </Tailwind>
    </Html>
  );
}

interface ButtonProps {
  href: string;
  children: React.ReactNode;
}

export function Button({ href, children }: ButtonProps) {
  return (
    <ReactEmailButton
      href={href}
      className="bg-ink text-paper-warm no-underline rounded-[2px] px-8 py-3.5 font-mono font-medium text-[11px] uppercase tracking-[0.18em] border border-ink leading-tight"
    >
      {children}
    </ReactEmailButton>
  );
}

interface DividerProps {
  className?: string;
}

export function Divider({ className }: DividerProps) {
  return <Hr className={`border-light-border my-7 ${className ?? ''}`} />;
}
