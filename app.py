import streamlit as st
import os
from dotenv import load_dotenv
from client import DeepSeekClient
from analyst import PolymarketAnalyst
from polymarket import PolymarketClient
from simulation import BettingSimulator

# Load env variables
load_dotenv()

st.set_page_config(page_title="DeepSeek Polymarket Predictor", page_icon="🔮", layout="wide")

st.title("🔮 DeepSeek Polymarket Predictor")
st.markdown("Analyze Polymarket events with AI-powered insights.")

# Cache the analysis to save tokens
@st.cache_data(show_spinner=False)
def analyze_market_cached(market_info, _api_key, mode="full", model="deepseek-chat", temperature=1.0):
    """
    Cached wrapper for market analysis.
    """
    client = DeepSeekClient(api_key=_api_key)
    analyst = PolymarketAnalyst(client)
    return analyst.analyze_market(market_info, mode=mode, model=model, temperature=temperature)

# Sidebar
st.sidebar.header("Settings")

# Sidebar Configuration
with st.sidebar:
    # Compact Profile Selector
    st.markdown("### 👤 Profile")
    
    # Find existing profiles using storage backend
    from storage import get_storage
    # Use a temporary storage instance to list profiles (defaulting to Default profile to init)
    temp_storage = get_storage("Default")
    profiles = temp_storage.list_profiles()
    profiles.append("➕ Create New...")
    
    # Session state for profile
    if 'current_profile' not in st.session_state:
        st.session_state['current_profile'] = "Default"
        
    selected_profile = st.selectbox("Select Profile", profiles, index=profiles.index(st.session_state['current_profile']) if st.session_state['current_profile'] in profiles else 0, label_visibility="collapsed")
    
    if selected_profile == "➕ Create New...":
        with st.container():
            new_profile_name = st.text_input("Name", placeholder="New Profile Name")
            if st.button("Create", use_container_width=True):
                if new_profile_name and new_profile_name not in profiles:
                    st.session_state['current_profile'] = new_profile_name
                    st.success(f"Created '{new_profile_name}'!")
                    st.rerun()
                elif new_profile_name in profiles:
                    st.error("Exists")
    else:
        if selected_profile != st.session_state['current_profile']:
            st.session_state['current_profile'] = selected_profile
            st.rerun()

    # Collapsible Settings
    with st.expander("⚙️ Settings", expanded=False):
        api_key = st.text_input("DeepSeek Key", type="password", value=os.getenv("DEEPSEEK_API_KEY", ""))
        
        st.caption("🤖 AI Model")
        ds_model = st.selectbox("Model", ["deepseek-chat", "deepseek-reasoner"], index=0, label_visibility="collapsed")
        ds_temp = st.slider("Temp", 0.0, 1.5, 1.0)

# Initialize Simulator with selected profile
current_profile = st.session_state['current_profile']
if 'simulator' not in st.session_state or st.session_state.get('simulator_profile') != current_profile:
    st.session_state['simulator'] = BettingSimulator(current_profile)
    st.session_state['simulator_profile'] = current_profile

# Sidebar Balance
st.sidebar.divider()
st.sidebar.markdown(f"### 💰 Wallet: ${st.session_state['simulator'].balance:,.2f}")

# Main Navigation
tab_markets, tab_portfolio = st.tabs(["📉 Markets", "📂 Portfolio"])

with tab_markets:
    # Removed "Science" as requested
    category = st.sidebar.selectbox("Category", ["Top", "Trending", "Politics", "NBA", "Football", "Soccer", "Crypto"])
    timeframe = st.sidebar.selectbox("Timeframe", ["Any", "1d", "1w"])
    sort_by = st.sidebar.selectbox("Sort By", ["Volume", "Liquidity", "Date (Newest)", "Date (Ending Soon)"])
    limit = st.sidebar.slider("Max Events", 1, 100, 20) 

    if st.sidebar.button("Fetch Events"):
        with st.spinner("Fetching events..."):
            try:
                poly_client = PolymarketClient()
                
                tag_id = None
                # Trending is essentially "Top" but we'll enforce sorting by Volume later if selected
                if category not in ["Top", "Trending"]:
                    tag_id = poly_client.get_tag_id(category)
                    if not tag_id:
                        st.warning(f"Could not find tag for {category}. Fetching generic events.")
                
                # Fetch significantly more events to ensure filtering works
                fetch_limit = 200 
                if category in ["Top", "Trending"] and timeframe != "Any":
                    fetch_limit = 500
                
                events = poly_client.fetch_events(tag_id=tag_id, limit=fetch_limit)
                
                if timeframe != "Any":
                    events = poly_client.filter_events(events, timeframe)
                
                # Sorting Logic
                if category == "Trending":
                    events = [e for e in events if float(e.get("volume") or 0) > 1000 or float(e.get("liquidity") or 0) > 1000]
                
                if sort_by == "Volume":
                    events.sort(key=lambda x: float(x.get("volume") or 0), reverse=True)
                elif sort_by == "Liquidity":
                    events.sort(key=lambda x: float(x.get("liquidity") or 0), reverse=True)
                elif sort_by == "Date (Newest)":
                    events.sort(key=lambda x: x.get("creationDate") or "", reverse=True)
                elif sort_by == "Date (Ending Soon)":
                    events.sort(key=lambda x: x.get("endDate") or "9999-12-31")
                
                events = events[:limit]
                
                st.session_state['events'] = events
                st.session_state['analysis_results'] = {} 
                
                if not events:
                    st.warning("No events found matching your criteria. Try increasing 'Max Events' or changing the timeframe.")
                
            except Exception as e:
                st.error(f"Error fetching events: {e}")

    # Display Events
    if 'events' in st.session_state:
        events = st.session_state['events']
        st.markdown(f"### Found {len(events)} Events")
        
        for i, event in enumerate(events):
            title = event.get("title")
            description = event.get("description")
            slug = event.get("slug")
            image_url = event.get("image")
            volume = float(event.get("volume") or 0)
            liquidity = float(event.get("liquidity") or 0)
            creation_date = event.get("creationDate")
            end_date = event.get("endDate")
            markets = event.get("markets", [])
            
            # Accordion Header
            header = f"**{title}**"
            if volume > 0:
                header += f" | 📊 ${volume:,.0f}"
            
            with st.expander(header, expanded=False):
                # Event Details
                c1, c2 = st.columns([1, 4])
                with c1:
                    if image_url:
                        st.image(image_url, use_container_width=True)
                    else:
                        st.markdown("🖼️ No Image")
                
                with c2:
                    st.caption(f"Liquidity: ${liquidity:,.0f} | Ends: {end_date[:10] if end_date else 'N/A'}")
                    st.markdown(f"[View on Polymarket](https://polymarket.com/event/{slug})")
                    if description:
                        st.write(description)
            
                # Markets Table
                if markets:
                    st.markdown("#### 📊 Markets & Betting")
                    # Get active bets for position lookup
                    active_bets = st.session_state['simulator'].get_portfolio()
                    my_positions = {}
                    for b in active_bets:
                        if b['status'] == 'OPEN':
                            my_positions[b['market']] = b['outcome']

                    # Prepare data for dataframe
                    market_data = []
                    for m in markets:
                        question = m.get("question")
                        m_end_date = m.get("endDate")[:10] if m.get("endDate") else "N/A"
                        market_id = m.get("id")
                        
                        # Check for position
                        my_pos = my_positions.get(question, "")
                        
                        row = {
                            "Market": question, 
                            "End Date": m_end_date, 
                            "My Position": my_pos,
                            "_raw_outcomes": m.get("outcomePrices"), 
                            "_id": market_id, 
                            "_event": title
                        }
                        
                        # Try to parse outcomes and prices
                        try:
                            outcome_names = m.get("outcomes")
                            outcome_prices = m.get("outcomePrices")
                            
                            if isinstance(outcome_names, str):
                                import json
                                outcome_names = json.loads(outcome_names)
                            if isinstance(outcome_prices, str):
                                import json
                                outcome_prices = json.loads(outcome_prices)
                                
                            if isinstance(outcome_names, list) and isinstance(outcome_prices, list):
                                # Map names to prices
                                outcomes_map = {}
                                for name, price in zip(outcome_names, outcome_prices):
                                    outcomes_map[name] = price
                                
                                # Check for Yes/No
                                if "Yes" in outcomes_map and "No" in outcomes_map:
                                    row["Yes"] = float(outcomes_map["Yes"]) * 100
                                    row["No"] = float(outcomes_map["No"]) * 100
                                    row["_yes_price"] = float(outcomes_map["Yes"])
                                    row["_no_price"] = float(outcomes_map["No"])
                                else:
                                    # Other outcomes
                                    parts = []
                                    for name, price in outcomes_map.items():
                                        val = float(price) * 100
                                        parts.append(f"{name}: {val:.0f}%")
                                    row["Outcomes"] = ", ".join(parts)
                            else:
                                 row["Outcomes"] = str(outcome_prices)
                        except Exception:
                            prices = m.get("outcomePrices")
                            row["Outcomes"] = str(prices) if prices else "N/A"

                        market_data.append(row)
                    
                    # Sort by Yes Probability if requested
                    market_data.sort(key=lambda x: x.get("Yes", 0), reverse=True)

                    # Create dataframe
                    import pandas as pd
                    df = pd.DataFrame(market_data)
                    
                    # Display Table
                    display_cols = ["Market"]
                    if "Yes" in df.columns: display_cols.extend(["Yes", "No"])
                    if "Outcomes" in df.columns: display_cols.append("Outcomes")
                    display_cols.append("End Date")
                    # Add My Position if any exist
                    if df["My Position"].any():
                        display_cols.insert(1, "My Position") # Put it early
                    
                    # Filter cols that actually exist
                    display_cols = [c for c in display_cols if c in df.columns]
                    
                    # Configure columns
                    column_config = {
                        "Market": st.column_config.TextColumn("Market", width="large"),
                        "End Date": st.column_config.TextColumn("End Date", width="small"),
                        "My Position": st.column_config.TextColumn("My Position", width="small", help="Your active bet"),
                    }
                    if "Yes" in df.columns:
                        column_config["Yes"] = st.column_config.ProgressColumn("Yes", format="%.0f%%", min_value=0, max_value=100)
                    if "No" in df.columns:
                        column_config["No"] = st.column_config.ProgressColumn("No", format="%.0f%%", min_value=0, max_value=100)

                    st.dataframe(df[display_cols], use_container_width=True, hide_index=True, column_config=column_config)
                    
                    # Check if already bet on this event
                    # This check needs to be done per market, not per event.
                    # The original instruction had `market['id']` which is not defined here.
                    # We need to iterate through markets to check for existing bets.
                    for market_item in markets:
                        existing_bet_for_market = next((b for b in st.session_state['simulator'].bets if b['market_id'] == market_item['id']), None)
                        if existing_bet_for_market:
                            st.info(f"✅ You have a position on {existing_bet_for_market['outcome']} (${existing_bet_for_market['amount']}) for market: {existing_bet_for_market['market_question']}")
                            break # Only show one indicator per event for simplicity, or iterate for each market

                    # Betting UI
                    st.markdown("#### 💰 Place a Bet")
                    # Find selected market data
                    selected_market = next((d for d in market_data if d["Market"] == selected_market_q), None)
                    
                    if selected_market:
                        outcomes_list = []
                        if "Yes" in selected_market:
                            outcomes_list = ["Yes", "No"]
                        else:
                            # Parse outcomes string back to list? Or just use raw if available
                            # Simplified: just support Yes/No for now or generic input
                            outcomes_list = ["Yes", "No"] # Fallback
                        
                        with c_b2:
                            selected_outcome = st.selectbox("Outcome", outcomes_list, key=f"bet_outcome_{i}")
                        
                        with c_b3:
                            bet_amount = st.number_input("Amount ($)", min_value=1.0, value=10.0, step=1.0, key=f"bet_amount_{i}")
                        
                        with c_b4:
                            # Determine price
                            price = 0.5
                            # Try to get specific price for outcome
                            if selected_market.get(f"_{selected_outcome.lower()}_price"):
                                price = selected_market.get(f"_{selected_outcome.lower()}_price")
                            
                            if st.button(f"Bet @ {price*100:.1f}¢", key=f"place_bet_{i}"):
                                success, msg = st.session_state['simulator'].place_bet(
                                    market_question=selected_market_q,
                                    outcome=selected_outcome,
                                    amount=bet_amount,
                                    price=price,
                                    event_title=title,
                                    market_id=selected_market.get("_id")
                                )
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
            
                # Analysis Section
                st.divider()
                c_an1, c_an2 = st.columns(2)
                
                analyze_clicked = False
                analysis_mode = "full"
                
                with c_an1:
                    if st.button("⚡ Quick Bet Rec", key=f"analyze_quick_{i}", use_container_width=True):
                        analyze_clicked = True
                        analysis_mode = "quick"
                
                with c_an2:
                    if st.button("🧠 Full Analysis", key=f"analyze_full_{i}", use_container_width=True):
                        analyze_clicked = True
                        analysis_mode = "full"
                
                if analyze_clicked:
                    with st.spinner(f"Running {analysis_mode} analysis..."):
                        # Prepare market info for analysis
                        market_info = f"Event: {title}\nDescription: {description}\n"
                        for m in markets[:5]: # Limit to top 5 markets
                            market_info += f"- Market: {m.get('question')}, Outcomes: {m.get('outcomePrices')}\n"
                        
                        try:
                            # Use slug + mode as key
                            cache_key = f"{slug}_{analysis_mode}"
                            analysis = analyze_market_cached(market_info, api_key, mode=analysis_mode, model=ds_model, temperature=ds_temp)
                            st.session_state['analysis_results'][slug] = analysis 
                        except Exception as e:
                            error_msg = str(e)
                            if "402" in error_msg:
                                st.error("⚠️ Insufficient Balance")
                            else:
                                st.error(f"Error: {e}")

                # Display Analysis Result
                if slug in st.session_state.get('analysis_results', {}):
                    result = st.session_state['analysis_results'][slug]
                    st.markdown("### 🤖 DeepSeek Analysis")
                    
                    if isinstance(result, dict):
                        st.info(f"**Summary:** {result.get('summary')}")
                        
                        # Display Bets
                        bets = result.get("bets", [])
                        if bets:
                            st.markdown("#### 🎯 Recommended Bets")
                            for b_idx, bet in enumerate(bets):
                                with st.container():
                                    b_c1, b_c2 = st.columns([3, 1])
                                    with b_c1:
                                        st.markdown(f"**{bet.get('market_question')}**")
                                        st.write(f"Pick: **{bet.get('prediction')}** | Conf: {bet.get('confidence')}")
                                        st.caption(f"Reason: {bet.get('reasoning')}")
                                    with b_c2:
                                        # Auto-Bet Button
                                        if st.button("Place Bet", key=f"autobet_{i}_{b_idx}"):
                                            # Logic to find market and place bet
                                            # We need to match 'market_question' to actual markets
                                            target_q = bet.get('market_question')
                                            target_outcome = bet.get('prediction')
                                            
                                            # Find matching market
                                            matched_market = None
                                            # Try exact match
                                            for m in markets:
                                                if m.get("question") == target_q:
                                                    matched_market = m
                                                    break
                                            
                                            # Try partial match if no exact
                                            if not matched_market:
                                                for m in markets:
                                                    if target_q in m.get("question", ""):
                                                        matched_market = m
                                                        break
                                            
                                            # Fallback to first market if single market event
                                            if not matched_market and len(markets) == 1:
                                                matched_market = markets[0]
                                                
                                            if matched_market:
                                                # Determine price
                                                price = 0.5 # Default/Fallback
                                                
                                                # Try to get real price
                                                try:
                                                    o_names = matched_market.get("outcomes")
                                                    o_prices = matched_market.get("outcomePrices")
                                                    if isinstance(o_names, str): import json; o_names = json.loads(o_names)
                                                    if isinstance(o_prices, str): import json; o_prices = json.loads(o_prices)
                                                    
                                                    if isinstance(o_names, list) and isinstance(o_prices, list):
                                                        if target_outcome in o_names:
                                                            idx = o_names.index(target_outcome)
                                                            price = float(o_prices[idx])
                                                except Exception as e:
                                                    print(f"Error finding price: {e}")

                                                # Use recommended_amount from the bet, or a default
                                                recommended_amount = bet.get('recommended_amount', 10.0) 

                                                success, msg = st.session_state['simulator'].place_bet(
                                                    market_question=matched_market.get("question"),
                                                    outcome=target_outcome,
                                                    amount=recommended_amount,
                                                    price=price,
                                                    event_title=title,
                                                    market_id=matched_market.get("id")
                                                )
                                                if success:
                                                    st.success(f"Bet placed! ({msg})")
                                                    st.rerun()
                                                else:
                                                    st.error(msg)
                                            else:
                                                st.error("Could not find matching market.")
                        
                    else:
                        st.write(result)
            
            st.divider()

with tab_portfolio:
    st.markdown("## 📂 My Portfolio")
    
    # Refresh Results Button
    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        if st.button("🔄 Check Results & Prices"):
            with st.spinner("Checking resolutions and prices..."):
                poly_client = PolymarketClient()
                updated = st.session_state['simulator'].update_results(poly_client)
                if updated > 0:
                    st.success(f"Updated {updated} bets!")
                else:
                    st.info("Prices updated.")
                st.rerun()
    
    portfolio = st.session_state['simulator'].get_portfolio()
    
    if portfolio:
        # Analytics
        total_bets = len(portfolio)
        won_bets = len([b for b in portfolio if b['status'] == 'WON'])
        lost_bets = len([b for b in portfolio if b['status'] == 'LOST'])
        open_bets = len([b for b in portfolio if b['status'] == 'OPEN'])
        
        win_rate = (won_bets / (won_bets + lost_bets)) * 100 if (won_bets + lost_bets) > 0 else 0
        
        start_balance = 1000.0
        current_balance = st.session_state['simulator'].balance
        pnl = current_balance - start_balance
        
        # Compact Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Bets", total_bets)
        c2.metric("Win Rate", f"{win_rate:.0f}%")
        c3.metric("Open", open_bets)
        c4.metric("PnL", f"${pnl:,.2f}", delta=f"{pnl:,.2f}")
        
        st.divider()
        
        # Active Bets - Simpler List
        st.markdown("### 🟢 Active Bets")
        active_bets = [b for b in portfolio if b['status'] == 'OPEN']
        
        if active_bets:
            # Create a clean dataframe for active bets
            import pandas as pd
            df_active = pd.DataFrame(active_bets)
            
            # Ensure current_price exists (backfill with entry price if missing)
            if 'current_price' not in df_active.columns:
                df_active['current_price'] = df_active['price']
            else:
                df_active['current_price'] = df_active['current_price'].fillna(df_active['price'])
            
            # Calculate Unrealized PnL
            # (Current Price - Entry Price) * (Amount / Entry Price)
            # Amount / Entry Price = Contracts
            df_active['contracts'] = df_active['amount'] / df_active['price']
            df_active['current_val'] = df_active['contracts'] * df_active['current_price']
            df_active['unrealized_pnl'] = df_active['current_val'] - df_active['amount']
            df_active['roi'] = (df_active['unrealized_pnl'] / df_active['amount']) * 100
            
            # Format for display
            df_display = df_active[['event', 'market', 'outcome', 'amount', 'price', 'current_price', 'unrealized_pnl', 'roi']].copy()
            df_display['price'] = df_display['price'].apply(lambda x: f"{x*100:.1f}¢")
            df_display['current_price'] = df_display['current_price'].apply(lambda x: f"{x*100:.1f}¢")
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "event": st.column_config.TextColumn("Event", width="medium"),
                    "market": st.column_config.TextColumn("Market", width="large"),
                    "outcome": st.column_config.TextColumn("Pick", width="small"),
                    "amount": st.column_config.NumberColumn("Invested", format="$%.2f"),
                    "price": st.column_config.TextColumn("Entry"),
                    "current_price": st.column_config.TextColumn("Current"),
                    "unrealized_pnl": st.column_config.NumberColumn("PnL", format="$%.2f"),
                    "roi": st.column_config.NumberColumn("ROI", format="%.1f%%"),
                }
            )
            
            # Individual Re-Analyze (Optional, maybe keep it simple as requested)
            # User asked for "simpler list", so maybe removing the expanders is better.
            # But the "Re-Analyze" feature is cool. Let's add it below the table or as a selector?
            # Or just keep it simple for now as requested.
            
        else:
            st.info("No active bets.")

        # History Table (Compact)
        st.markdown("### 📜 History")
        history_bets = [b for b in portfolio if b['status'] != 'OPEN']
        if history_bets:
            import pandas as pd
            df_hist = pd.DataFrame(history_bets)
            df_hist['date'] = df_hist['date'].apply(lambda x: x[:10])
            df_hist['return'] = df_hist.apply(lambda x: x['potential_payout'] - x['amount'] if x['status'] == 'WON' else -x['amount'], axis=1)
            
            st.dataframe(
                df_hist[['date', 'event', 'outcome', 'amount', 'return', 'status']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "date": "Date",
                    "event": "Event",
                    "outcome": "Pick",
                    "amount": st.column_config.NumberColumn("Bet", format="$%.2f"),
                    "return": st.column_config.NumberColumn("PnL", format="$%.2f"),
                    "status": "Result"
                }
            )
        else:
            st.caption("No history yet.")
            
    else:
        st.info("No bets placed yet.")
