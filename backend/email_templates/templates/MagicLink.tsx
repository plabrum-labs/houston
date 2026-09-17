import { Section, Text } from '@react-email/components';
import * as React from 'react';
import { BaseLayout, Button, Divider } from './components';

interface MagicLinkProps {
  magic_link_url: string;
  expiration_minutes: string | number;
}

export default function MagicLink({
  magic_link_url = 'https://app.marlinsurvey.com/auth/magic-link?token=example',
  expiration_minutes = 15,
}: MagicLinkProps) {
  return (
    <BaseLayout
      preview="Sign in to your account"
      footerNote="This email was sent because a sign-in was requested for your account."
    >
      <Text className="font-mono text-[10px] text-brass-deep uppercase tracking-[0.28em] m-0 mb-3">
        Sign in
      </Text>
      <Text className="font-serif text-[26px] leading-tight text-ink m-0 mb-5">
        Sign in to your account
      </Text>

      <Text className="font-body text-[15px] leading-relaxed text-ink-muted m-0 mb-7">
        Click the button below to securely sign in to Marlin Survey. This link expires in{' '}
        {expiration_minutes} minutes for your security.
      </Text>

      <Section className="mb-8">
        <Button href={magic_link_url}>Continue to Marlin Survey</Button>
      </Section>

      <Divider />

      {/* Copyable link */}
      <Text className="font-mono text-[10px] text-brass-deep uppercase tracking-[0.22em] m-0 mb-2">
        Or copy this link
      </Text>
      <div className="bg-paper-warm border border-light-border rounded-[2px] px-4 py-3.5">
        <Text className="font-mono text-[12px] break-all m-0 leading-normal text-ink-muted">
          {magic_link_url}
        </Text>
      </div>

      <Divider />

      {/* Security notice */}
      <div className="bg-paper-warm rounded-[2px] border border-light-border px-4 py-4">
        <Text className="font-body text-[14px] leading-relaxed text-ink-muted m-0">
          <strong className="text-ink font-semibold">Didn&rsquo;t request this?</strong>
          <br />
          You can safely ignore this email. This link can only be used once and expires automatically.
        </Text>
      </div>
    </BaseLayout>
  );
}
