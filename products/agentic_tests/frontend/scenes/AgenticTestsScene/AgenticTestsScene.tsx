import { useActions, useValues } from 'kea'

import { LemonButton, LemonTable, LemonTag, LemonTagType, Link, Tooltip } from '@posthog/lemon-ui'

import { TZLabel } from 'lib/components/TZLabel'
import { SceneExport } from 'scenes/sceneTypes'
import { urls } from 'scenes/urls'

import { SceneContent } from '~/layout/scenes/components/SceneContent'
import { SceneTitleSection } from '~/layout/scenes/components/SceneTitleSection'

import { AgenticTest } from '../../types'
import { agenticTestsSceneLogic } from './agenticTestsSceneLogic'

const STATUS_TAG: Record<string, { type: LemonTagType; label: string }> = {
    passed: { type: 'success', label: 'Passing' },
    failed: { type: 'danger', label: 'Failing' },
    running: { type: 'primary', label: 'Running' },
    timeout: { type: 'warning', label: 'Timeout' },
    error: { type: 'danger', label: 'Error' },
}

function statusFor(test: AgenticTest): { type: LemonTagType; label: string } {
    if (test.status === 'paused') {
        return { type: 'muted', label: 'Paused' }
    }
    if (test.status === 'proposed') {
        return { type: 'highlight', label: 'Proposed' }
    }
    if (!test.last_run) {
        return { type: 'muted', label: 'Pending' }
    }
    return STATUS_TAG[test.last_run.status] ?? { type: 'muted', label: test.last_run.status }
}

export function AgenticTestsScene(): JSX.Element {
    const { tests, testsLoading, passingCount, failingCount, proposedCount } = useValues(agenticTestsSceneLogic)
    const { deleteTest, runNow, pauseTest, activateTest } = useActions(agenticTestsSceneLogic)

    return (
        <SceneContent>
            <SceneTitleSection
                name="Agentic tests"
                description="LLM-driven browser checks against your product, seeded by session replays."
                resourceType={{ type: 'agentic_tests' as any }}
                actions={
                    <LemonButton type="primary" to={(urls as any).agenticTestNew()} data-attr="agentic-tests-new">
                        New test
                    </LemonButton>
                }
            />
            <div className="flex gap-4 mb-4 text-sm">
                <span>
                    <strong>{proposedCount}</strong> proposed
                </span>
                <span>
                    <strong>{passingCount}</strong> passing
                </span>
                <span>
                    <strong>{failingCount}</strong> failing
                </span>
                <span>
                    <strong>{tests.length}</strong> total
                </span>
            </div>
            <LemonTable
                dataSource={tests}
                loading={testsLoading}
                rowKey="id"
                emptyState="No agentic tests yet — create one or wait for proposed tests to land."
                columns={[
                    {
                        title: 'Name',
                        key: 'name',
                        render: (_, test) => (
                            <Link to={(urls as any).agenticTest(test.id)} data-attr="agentic-test-row-link">
                                {test.name}
                            </Link>
                        ),
                    },
                    {
                        title: 'Status',
                        key: 'status',
                        render: (_, test) => {
                            const status = statusFor(test)
                            return (
                                <Tooltip title={test.last_run?.error_message || ''}>
                                    <LemonTag type={status.type}>{status.label}</LemonTag>
                                </Tooltip>
                            )
                        },
                    },
                    {
                        title: 'Last run',
                        key: 'last_run',
                        render: (_, test) =>
                            test.last_run_at ? (
                                <TZLabel time={test.last_run_at} />
                            ) : (
                                <span className="text-muted">—</span>
                            ),
                    },
                    {
                        title: '',
                        key: 'actions',
                        render: (_, test) => (
                            <div className="flex gap-1">
                                {test.status === 'proposed' ? (
                                    <LemonButton
                                        size="xsmall"
                                        type="primary"
                                        onClick={() => activateTest(test.id)}
                                        data-attr="agentic-test-accept"
                                    >
                                        Accept
                                    </LemonButton>
                                ) : (
                                    <LemonButton
                                        size="xsmall"
                                        onClick={() => runNow(test.id)}
                                        data-attr="agentic-test-run-now"
                                    >
                                        Run now
                                    </LemonButton>
                                )}
                                {test.status === 'active' ? (
                                    <LemonButton size="xsmall" onClick={() => pauseTest(test.id)}>
                                        Pause
                                    </LemonButton>
                                ) : test.status === 'paused' ? (
                                    <LemonButton size="xsmall" onClick={() => activateTest(test.id)}>
                                        Resume
                                    </LemonButton>
                                ) : null}
                                <LemonButton
                                    size="xsmall"
                                    status="danger"
                                    onClick={() => deleteTest(test.id)}
                                    data-attr="agentic-test-delete"
                                >
                                    Delete
                                </LemonButton>
                            </div>
                        ),
                    },
                ]}
            />
        </SceneContent>
    )
}

export const scene: SceneExport = {
    component: AgenticTestsScene,
    logic: agenticTestsSceneLogic,
}

export default AgenticTestsScene
