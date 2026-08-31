import React, { useMemo, useState } from 'react';
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

type ContactStatus = 'unavailable' | 'discovered' | 'format_validated' | 'ownership_verified';
type VerificationState =
  | 'not_requested'
  | 'pending'
  | 'ownership_verified'
  | 'failed'
  | 'expired'
  | 'revoked';

interface ChallengeSnapshot {
  challenge_id: string;
  state: VerificationState;
  previous_state: VerificationState;
  method: 'email_link' | 'sms_otp';
  recipient_fingerprint: string;
  delivery_status: 'dry_run_preview' | 'provider_required';
  attempts: number;
  expires_at: string;
  verified_at: string | null;
  preview_token?: string;
}

interface Props {
  contactStatus: ContactStatus;
  email: string;
  phone: string;
  emailEstimated: boolean;
}

function errorMessage(error: unknown): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  const messages: Record<string, string> = {
    invalid_email: '이메일 형식을 확인해 주세요.',
    invalid_phone: '전화번호 형식을 확인해 주세요.',
    invalid_verification_token: '확인 코드가 일치하지 않습니다.',
    contact_verification_expired: '확인 요청이 만료되었습니다. 다시 요청해 주세요.',
    contact_verification_attempts_exceeded: '확인 시도 횟수를 초과했습니다.',
    contact_already_verified: '이미 소유 확인이 완료된 연락처입니다.',
    contact_verification_not_found: '확인 요청을 찾을 수 없습니다.',
  };
  return messages[String(detail || '')] || '연락처 확인 요청을 처리하지 못했습니다.';
}

const ContactOwnershipPanel: React.FC<Props> = ({
  contactStatus,
  email,
  phone,
  emailEstimated,
}) => {
  const target = useMemo(() => {
    if (email && !emailEstimated) return { channel: 'email' as const, recipient: email };
    if (phone) return { channel: 'sms' as const, recipient: phone };
    return null;
  }, [email, phone, emailEstimated]);
  const [snapshot, setSnapshot] = useState<ChallengeSnapshot | null>(null);
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const effectiveState: VerificationState =
    snapshot?.state || (contactStatus === 'ownership_verified' ? 'ownership_verified' : 'not_requested');

  const requestChallenge = async () => {
    if (!target) return;
    setLoading(true);
    setError('');
    setToken('');
    try {
      const { data } = await api.post<ChallengeSnapshot>('/v1/contact-verifications', target);
      setSnapshot(data);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  const confirmChallenge = async () => {
    if (!snapshot?.challenge_id || !token.trim()) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await api.post<ChallengeSnapshot>(
        `/v1/contact-verifications/${snapshot.challenge_id}/confirm`,
        { token: token.trim() },
      );
      setSnapshot(data);
      setToken('');
    } catch (confirmError) {
      setError(errorMessage(confirmError));
    } finally {
      setLoading(false);
    }
  };

  const revokeVerification = async () => {
    if (!snapshot?.challenge_id) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await api.post<ChallengeSnapshot>(
        `/v1/contact-verifications/${snapshot.challenge_id}/revoke`,
      );
      setSnapshot(data);
    } catch (revokeError) {
      setError(errorMessage(revokeError));
    } finally {
      setLoading(false);
    }
  };

  if (contactStatus === 'unavailable') {
    return (
      <div className="flex items-center gap-2 mt-4 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 w-fit">
        <AlertCircle className="h-4 w-4 text-slate-500" />
        <span className="text-xs font-medium text-slate-600">연락처 없음</span>
        <span className="text-[10px] text-slate-400">자료 내 확인 불가 — 발송 불가</span>
      </div>
    );
  }

  if (!target) {
    return (
      <div className="flex items-center gap-2 mt-4 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
        <AlertCircle className="h-4 w-4 text-amber-600" />
        <span className="text-xs text-amber-700">추정 이메일만 있어 소유 확인 요청을 보낼 수 없습니다.</span>
      </div>
    );
  }

  if (effectiveState === 'ownership_verified') {
    return (
      <div className="mt-4 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-3">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span className="text-xs font-semibold text-emerald-700">연락처 소유 확인 완료</span>
          {snapshot?.verified_at && <span className="text-[10px] text-emerald-600">{snapshot.verified_at}</span>}
        </div>
        {snapshot?.challenge_id && (
          <Button variant="ghost" size="sm" className="h-7 mt-2 text-xs text-slate-500" onClick={revokeVerification} disabled={loading}>
            확인 상태 철회
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="mt-4 bg-amber-50 border border-amber-100 rounded-lg px-3 py-3 space-y-2">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-amber-600" />
        <span className="text-xs font-medium text-amber-700">
          {snapshot ? '소유 확인 대기 중' : '연락처 보유 — 소유 미확인'}
        </span>
        <span className="text-[10px] text-amber-500">
          {target.channel === 'email' ? '이메일 링크' : 'SMS OTP'} 방식
        </span>
      </div>

      {!snapshot && (
        <Button size="sm" className="h-7 text-xs" onClick={requestChallenge} disabled={loading}>
          {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <ShieldCheck className="h-3 w-3 mr-1" />}
          소유 확인 요청
        </Button>
      )}

      {snapshot?.delivery_status === 'provider_required' && (
        <p className="text-xs text-amber-700">실제 전달 채널이 아직 연결되지 않아 확인 링크를 발송하지 않았습니다.</p>
      )}

      {snapshot?.preview_token && snapshot.state === 'pending' && (
        <div className="space-y-2">
          <p className="text-[10px] text-slate-500">개발용 dry-run 확인 코드: {snapshot.preview_token}</p>
          <div className="flex gap-2">
            <input
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder="확인 코드 입력"
              className="h-8 flex-1 rounded-md border border-slate-300 bg-white px-2 text-xs"
            />
            <Button size="sm" className="h-8 text-xs" onClick={confirmChallenge} disabled={loading || !token.trim()}>
              {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}확인
            </Button>
          </div>
        </div>
      )}

      {snapshot && ['failed', 'expired', 'revoked'].includes(snapshot.state) && (
        <Button variant="outline" size="sm" className="h-7 text-xs" onClick={requestChallenge} disabled={loading}>
          <RefreshCw className="h-3 w-3 mr-1" />다시 요청
        </Button>
      )}

      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
};

export default ContactOwnershipPanel;

