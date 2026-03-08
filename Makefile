.PHONY: sim viewer agent dev

# Sim server (default: 10 FPS, 1 real sec = 1 sim day)
sim:
	cd $(CURDIR) && source .venv/bin/activate && python -m sim.server --time-warp 86400

# Viewer (Vite dev server)
viewer:
	cd $(CURDIR)/mission-visualizer && npm run dev

# Agent client
agent:
	cd $(CURDIR) && source .venv/bin/activate && python -m sim.agent_client

# All three in parallel (sim + viewer + agent)
dev:
	@echo "Starting sim server + viewer..."
	@echo "  Sim:    ws://localhost:8765"
	@echo "  Viewer: http://localhost:5173/?mode=live"
	@$(MAKE) -j2 sim viewer
