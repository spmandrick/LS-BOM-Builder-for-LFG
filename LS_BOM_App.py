import math
import streamlit as st
import pandas as pd

#Function to load custom CSS
def local_css(file_name):
   with open(file_name) as f:
       st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

#Load the CSS file
local_css("assets/style.css")

LS = "data/LS-Logo.jpg"
LFG = "data/LFG-Logo-App_Colors.jpg"

h1, h2, h3, h4 = st.columns([8,1,6,12])
with h1:
    st.image([LFG], width=250)
with h2:
    st.subheader("x")
with h3:
    st.image([LS], width=140)
with h4:
    st.header("BOM Builder")

#st.button("CSS Test Button", key="green_button")

st.space("small")
st.subheader("Switchboard Properties")
sb1, sb2, sb3 = st.columns(3)
with sb1:
    main_amp = st.select_slider("Main Amperage", options = [1200,1600,2000,2500,3000,4000], value = 4000)
with sb2:
    V = st.segmented_control("Voltage", options = ["120/208V", "277/480V"], default=None)
with sb3:
    kAIC = st.segmented_control("kAIC", options = [35, 50, 65, 100], default=None)

# BREAKER LOGIC -----------------------------------------------------------------------------------

df = pd.read_csv("data/LS_CBs.csv")
df.pop("Unnamed: 0")
df["Frame Rating"] = df["Frame Rating"].astype(int)
df["Amp Rating"] = df["Amp Rating"].str.extract('(\\d+)').astype(int)
df["Performance %"] = df["Performance %"].astype(int)
df["LSI"] = (df["Frame Rating"] >= 800) | (df["Trip Unit"].str.contains("ETS", na=False))

st.subheader("Breaker Properties")
brk1, brk2, brk3 = st.columns([3,2,5])
with brk1:
    amp_r = st.number_input("Amp Rating", min_value = 15, max_value = 4000, value = 4000, step = 5)
with brk2:
    Perf = st.segmented_control("Performance %", options = [80, 100], default=80)
with brk3:
    lsi = st.toggle("LSI Required", value=False)

#Filter by frame size
LS_frame_sizes = [150,250, 400, 600, 800, 1200, 1600, 2000, 2500, 3200, 4000]
fs = 0
for size in LS_frame_sizes:
    if amp_r <= size:
        fs = size
        break

# This below line does most of the filtering, and almost all of it for ACBs
result = df.query('`Amp Rating` >= @amp_r and `Frame Rating` == @fs')

# The only weird situation for ACBs, (for 3000A ACBs, we use 3200 frame with 3000A rating)
if fs == 3200 and amp_r <= 3000:
    result = result[result['Amp Rating'] == 3000]

#Filter by other options for MCCBs (all ACBs have LSI, 100% perf, ATU and 100kAIC)
if amp_r <= 1200:

    # Filter by performance %
    result = result[result['Performance %'] == Perf]

    # Filter by LSI (all breakers above 800A frame size have LSI)
    if fs < 800:
        result = result[result['LSI'] == lsi]
        
        # Filter by amp rating
        amp_r_list = [a for a in result['Amp Rating'].unique().tolist() if a >= amp_r]
        if amp_r == min(amp_r_list): # Exact match found, use FTU
            result = result[(result['Amp Rating'] == amp_r) & ((result['Trip Unit'].str.contains("FTU", na=False)) | (result['Trip Unit'].str.contains("ETS", na=False)))] # Picking exact amp rating with FTU
        else:   # No exact match, use ATU
            result = result[(result['Trip Unit'].str.contains("ATU", na=False)) | (result['Trip Unit'].str.contains("ETS", na=False))]
            amp_r_list = [a for a in result['Amp Rating'].unique().tolist() if a >= amp_r]
            result = result[result['Amp Rating'] == min(amp_r_list)] # Picking the minimum amp rating available
    else:
        amp_r_list = [a for a in result['Amp Rating'].unique().tolist() if a >= amp_r]
        result = result[result['Amp Rating'] == min(amp_r_list)] # Picking the minimum amp rating available

    # Filter by kAIC
    if V == "120/208V":
        kAIC_list = [k for k in result['240V kAIC'].unique().tolist() if k >= kAIC] # Filtering for kAIC options
        min_kAIC = min(kAIC_list) 
        result = result[result['240V kAIC'] == min_kAIC] # Picking the minimum kAIC available
    elif V == "277/480V":
        kAIC_list = [k for k in result['480V kAIC'].unique().tolist() if k >= kAIC] # Filtering for kAIC options
        min_kAIC = min(kAIC_list) 
        result = result[result['480V kAIC'] == min_kAIC] # Picking the minimum kAIC available

# May have multiple results with different breaking cpacities, so we pick the cheapest one here
cb = result[result['List Price'] == result['List Price'].min()]

st.space("small")
st.subheader("Recommended Breaker")
st.write(cb[['Item #', 'Part #', 'List Price', '240V kAIC', '480V kAIC']])

bom1, bom2 = st.columns([2,7])
with bom1:
    qty = st.number_input("Quantity to add", min_value = -1, max_value = 10, value = 1)
with bom2:
    b_type = st.segmented_control("Breaker Type", options = ["Main", "Branch"], default=None)

add_to_bom = st.button("**Add Breaker to Board BOM**", width = "stretch", type ="primary")

# BREAKER BOM SECTION----------------------------------------------------------------------------------------

st.space("medium")
BBOM_header1, BBOM_header2 = st.columns([3,1])
with BBOM_header1:
    st.subheader("Board Bill of Materials")
with BBOM_header2:
    reset = st.button("*Reset Board BOM*")

st.write('**Breakers**')

# Creating a copy of the dataframe to use for the BOM
if 'BOM_df' not in st.session_state:
    st.session_state.BOM_df = pd.read_csv("data/LS_CBs.csv")
    st.session_state.BOM_df.pop("Unnamed: 0")
    st.session_state.BOM_df["Frame Rating"] = st.session_state.BOM_df["Frame Rating"].astype(int)
    st.session_state.BOM_df["Amp Rating"] = st.session_state.BOM_df["Amp Rating"].str.extract('(\\d+)').astype(int)
    st.session_state.BOM_df["Performance %"] = st.session_state.BOM_df["Performance %"].astype(int)
    st.session_state.BOM_df.insert(0, 'Main Qty', 0)
    st.session_state.BOM_df.insert(1, 'Branch Qty', 0)

if add_to_bom:
    if b_type == "Main":
        st.session_state.BOM_df.loc[st.session_state.BOM_df['Item #'] == cb['Item #'].iloc[0], 'Main Qty'] += qty
    elif b_type == "Branch":
        st.session_state.BOM_df.loc[st.session_state.BOM_df['Item #'] == cb['Item #'].iloc[0], 'Branch Qty'] += qty
    else:
        st.warning(":red[Breaker not added. Please select a breaker type.]")

if reset:
    #st.write("BOM Reset")
    st.session_state.BOM_df["Main Qty"] = 0
    st.session_state.BOM_df["Branch Qty"] = 0

BOM_filter = (st.session_state.BOM_df['Main Qty'] > 0) | (st.session_state.BOM_df['Branch Qty'] > 0)
cbBOM = st.session_state.BOM_df[BOM_filter][['Main Qty', 'Branch Qty', 'Item #', 'Part #']]
st.write(cbBOM.head(10))

# STRAP BOM SECTION----------------------------------------------------------------------------------------

st.write("**Straps**")
if 'Strap_BOM_df' not in st.session_state:
    st.session_state.strap_df = pd.read_csv("data/LS_Straps.csv")
    st.session_state.strap_df.insert(0, 'Qty', 0)

st.session_state.branch_qtys = {150: 0, 250: 0, 400: 0, 600: 0, 800: 0, 1200: 0}
for brkr in st.session_state.BOM_df[st.session_state.BOM_df['Branch Qty'] > 0].itertuples():
    brkr_fr = brkr._6 # Frame rating is the 6th column in the dataframe
    brkr_qty = brkr._2 # Branch qty is the 2nd column in the dataframe
    #st.write(brkr_fr, brkr_qty)
    if brkr_fr in st.session_state.branch_qtys.keys(): # Frame rating is the 7th column in the dataframe
        st.session_state.branch_qtys[brkr_fr] += brkr_qty

X_spaces = 0
X_dict = {150: 4, 250: 4, 400: 6, 600: 6, 800: 9, 1200: 9}
st.session_state.strap_qtys = {150: 0, 250: 0, 400: 0, 600: 0, 800: 0, 1200: 0}
for fr, qty in st.session_state.branch_qtys.items():
    if qty > 0 and fr <= 400:
        strap_qty = math.ceil(qty / 2)
        st.session_state.strap_qtys[fr] += strap_qty
    else:
        strap_qty = qty
        st.session_state.strap_qtys[fr] += strap_qty
    X_spaces += strap_qty * X_dict[fr]

st.session_state.strap_df["Qty"] = st.session_state.strap_qtys.values()

strapBOM = st.session_state.strap_df[st.session_state.strap_df['Qty'] > 0][['Qty', 'Item #', 'Part #']]
st.write(strapBOM.head(10))

# INTERIOR BOM SECTION----------------------------------------------------------------------------------------

int1, int2 = st.columns([5,1])
with int1:
    st.write("**Interiors**")
with int2:
    st.write(f'X Spaces: \t {X_spaces}')

int_df = pd.read_csv("data/LS_Interiors.csv")
int = int_df[int_df['Amperage'] == int_df[int_df['Amperage'] >= main_amp]['Amperage'].min()]
int_Xs = int['X Spaces'].iloc[0]
int.insert(0, 'Qty', math.ceil(X_spaces / int_Xs))
if X_spaces > 0:
    intBOM = int[['Qty','Item #', 'Part #']]
else:
    # Just print empty list to look uniform
    intBOM = int[int['Amperage'] == 0][['Qty','Item #', 'Part #']]
st.write(intBOM)

# PROJECT BOM AND CSV SECTION ------------------------------------------------------------------------------------

if 'BOM' not in st.session_state:
    st.session_state.BOM = pd.DataFrame({'Board':[], 'Product':[], 'Qty':[], 'Item #':[], 'Part #':[]})
if 'board_list' not in st.session_state:
    st.session_state.board_list = []

st.space("small")
board_name = st.text_input("Switchboard Name")
add_to_proj_BOM = st.button("**Add Board BOM to Project BOM**", width = "stretch", type ="primary")
if add_to_proj_BOM:
    if board_name == '':
        st.warning(":red[Board BOM not added. Please indicate switchboard name above.]")
    elif board_name in st.session_state.board_list:
        st.warning(":red[Board with this name already created. Please change the name above or delete the board with this name below.]")
    else:
        st.session_state.board_list.append(board_name)
        for i, cb in cbBOM.iterrows():
            st.session_state.BOM.loc[len(st.session_state.BOM)] = [board_name, "Breaker", cb['Main Qty'] + cb['Branch Qty'], cb['Item #'], cb['Part #']]
        for i, strap in strapBOM.iterrows():
            st.session_state.BOM.loc[len(st.session_state.BOM)] = [board_name, "Strap", strap['Qty'], strap['Item #'], strap['Part #']]
        for i, interior in intBOM.iterrows():
            st.session_state.BOM.loc[len(st.session_state.BOM)] = [board_name, "Interior", interior['Qty'], interior['Item #'], interior['Part #']]

st.space("medium")
pbom1, pbom2 = st.columns([5,2])
with pbom1:
    st.subheader("Project Bill of Materials")
with pbom2:
    reset_PBOM = st.button("*Reset Project BOM*")

if reset_PBOM:
    st.session_state.BOM = pd.DataFrame({'Board':[], 'Qty':[], 'Item #':[], 'Part #':[]})

st.space("small")
dlt_brd1, dlt_brd2 = st.columns([7,1])
with dlt_brd1:
    brd_to_delete = st.selectbox("Select a board you may wish to delete", options = st.session_state.board_list, index = None)
with dlt_brd2:
    dlt_brd = st.button("*Delete Board*")

if dlt_brd:
    if brd_to_delete != None:
        st.session_state.board_list.remove(brd_to_delete)
        st.session_state.BOM = st.session_state.BOM[st.session_state.BOM['Board'] != brd_to_delete]
    else:
        st.warning(":red[No board deleted. Please select a board you wish to delete.]")

st.write(st.session_state.BOM)

st.space("small")
proj_name = st.text_input("Project Name")
st.download_button(label='**Download CSV**', data = st.session_state.BOM.to_csv().encode("utf-8"), file_name= f'{proj_name} LS BOM.csv', width = "stretch", type ="primary")