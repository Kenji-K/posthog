import { actions, kea, listeners, path, selectors } from 'kea'
import { loaders } from 'kea-loaders'

import api from 'lib/api'
import { getCurrentTeamId } from 'lib/utils/getAppContext'

import { AgenticTest } from '../../types'
import type { agenticTestsSceneLogicType } from './agenticTestsSceneLogicType'

const baseUrl = (): string => `api/projects/${getCurrentTeamId()}/agentic_tests/`

export const agenticTestsSceneLogic = kea<agenticTestsSceneLogicType>([
    path(['products', 'agentic_tests', 'frontend', 'scenes', 'AgenticTestsScene', 'agenticTestsSceneLogic']),
    actions({
        deleteTest: (id: string) => ({ id }),
        runNow: (id: string) => ({ id }),
        activateTest: (id: string) => ({ id }),
        pauseTest: (id: string) => ({ id }),
    }),
    loaders({
        tests: [
            [] as AgenticTest[],
            {
                loadTests: async () => {
                    const response = await api.get<{ results: AgenticTest[] }>(baseUrl())
                    return response.results
                },
            },
        ],
    }),
    listeners(({ actions }) => ({
        deleteTest: async ({ id }) => {
            await api.delete(`${baseUrl()}${id}/`)
            actions.loadTests()
        },
        runNow: async ({ id }) => {
            await api.create(`${baseUrl()}${id}/run_now/`, {})
            actions.loadTests()
        },
        activateTest: async ({ id }) => {
            await api.create(`${baseUrl()}${id}/activate/`, {})
            actions.loadTests()
        },
        pauseTest: async ({ id }) => {
            await api.create(`${baseUrl()}${id}/pause/`, {})
            actions.loadTests()
        },
    })),
    selectors({
        passingCount: [(s) => [s.tests], (tests) => tests.filter((t) => t.last_run?.status === 'passed').length],
        failingCount: [(s) => [s.tests], (tests) => tests.filter((t) => t.last_run?.status === 'failed').length],
        proposedCount: [(s) => [s.tests], (tests) => tests.filter((t) => t.status === 'proposed').length],
    }),
])
